class Args:
    def __init__(self):
        self.env = 'PongDeterministic-v4'  # BreakoutDeterministic-v4
        # self.env = 'BreakoutDeterministic-v4'
        self.lr = 1e-4
        self.gamma = 0.99
        self.tau = 1.00
        self.entropy_coef = 0.01
        self.value_loss_coef = 0.5
        self.max_grad_norm = 50
        self.seed = 1
        self.num_processes = 10
        self.num_steps = 20000
        self.max_episode_length = 1000000
        self.no_shared = False

