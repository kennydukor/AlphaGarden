from wrapperenv import WrapperEnv
from Garden import Garden

class SimAlphaGardenWrapper(WrapperEnv):
    def __init__(self, max_time_steps, plants, N, M, step, spread, light_amt):
        super(SimAlphaGardenWrapper, self).__init__(max_time_steps)
        self.plants = plants
        self.N = N
        self.M = M
        self.step = step
        self.spread = spread
        self.reset()
        self.light_amt = light_amt
        self.state = self.garden.get_state()

    '''
    Method called by the gym environment to execute an action.

    Parameters:
        action - list of (location, irrigation_amount) tuples, location is an
        (x, y) float64 tuple, irrigation_amount is a float64
    Returns:
        state - state of the environment after irrigation
    '''
    def take_action(self, current_step, action):
        self.garden.perform_timestep(self.light_amt, uniform_irrigation=False, irrigations=action)
        return self.garden.get_state()

    '''
    Method called by the gym environment to reset the simulator.
    '''
    def reset(self):
        self.garden = Garden(self.plants, self.N, self.M, self.step, self.spread)
