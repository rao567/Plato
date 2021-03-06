from model import ActorModel, CriticModel
import numpy as np
import torch
import torch.optim as optim
import torch.nn.functional as F
from torch.autograd import Variable


def chief(args, actor, critic, update_events, rolling_events, state_queue, queue, counter, queue_size):
    epoch = 0
    actor_optimizer = optim.Adam(actor.parameters(), lr=args.a_lr)
    critic_optimizer = optim.Adam(critic.parameters(), lr=args.c_lr)
    while True:
        epoch += 1
        for rank in range(args.num_processes):
            update_events[rank].wait()  # wait while get batch of data
        actor_old = ActorModel()
        actor_old.load_state_dict(actor.state_dict())  # update old actor parameters
        print('chief queue_size:', queue_size.get())
        data = [queue.get() for _ in range(queue_size.get())]  # receive collected data from workers
        # data = [queue.get() for _ in range(queue.qsize())]
        data = np.vstack(data)
        state_data = [state_queue.get() for _ in range(queue_size.get())]
        # state_data = [state_queue.get() for _ in range(state_queue.qsize())]
        queue_size.reset()
        states = []
        for worker_states in state_data:
            for state in worker_states:
                states.append(state)
        actions, returns = data[:, 0:1], data[:, 1:2]
        states = Variable(torch.FloatTensor(states))
        returns = Variable(torch.FloatTensor(returns))
        print(states.shape, actions.shape, returns.shape)
        batch_size = returns.shape[0]
        actions = Variable(torch.LongTensor(actions))
        print('chief get data')
        # print(states)
        # print(actions)
        # print(advantages)
        for _ in range(args.update_steps):
            # update actor and critic
            values = critic(states, batch_size=batch_size)
            advantages = returns - values
            adv_mean = advantages.mean()
            adv_std = advantages.std()
            advantages = (advantages - adv_mean) / adv_std
            print('adv', values.mean())
            logit = actor(states, batch_size=batch_size)
            log_probs = F.log_softmax(logit)
            # print('log_probs', log_probs)
            action_log_probs = log_probs.gather(1, actions)
            # print(action_log_probs)
            old_logit = actor_old(states, batch_size=batch_size)
            old_log_probs = F.log_softmax(old_logit)
            old_action_log_probs = old_log_probs.gather(1, actions)
            ratio = action_log_probs / old_action_log_probs + 1e-5
            # print('ratio', ratio)
            # ratio = torch.exp(action_log_probs / old_action_log_probs)
            surr1 = ratio * advantages
            surr2 = torch.clamp(ratio, 1.0 - args.clip, 1.0 + args.clip) * advantages
            actor_loss = -torch.min(surr1, surr2).mean()
            critic_loss = advantages.pow(2).mean()
            print('loss', actor_loss, critic_loss)
            # actor_optimizer.zero_grad()
            # critic_optimizer.zero_grad()
            actor.zero_grad()
            critic.zero_grad()
            actor_loss.backward(retain_graph=True)
            critic_loss.backward(retain_graph=True)
            torch.nn.utils.clip_grad_norm(actor.parameters(), 0.5)
            torch.nn.utils.clip_grad_norm(critic.parameters(), 0.5)
            actor_optimizer.step()
            critic_optimizer.step()
            print('update')
        print('update finished')
        # updating finished
        for rank in range(args.num_processes):
            update_events[rank].clear()
            rolling_events[rank].set()
        counter.reset()
        queue_size.reset()
        if epoch % 1000 == 0:
            path = 'results-1/actor.pt-' + str(epoch/1000)
            torch.save(actor.state_dict(), path)
            print('saved one model in epoch:', epoch)

