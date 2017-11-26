# Defined as a generic bot, can use multiple models
import itertools
import random
from collections import deque

import numpy as np
import tensorflow as tf

from actorcritic import PolicyGradientActorCritic
from input_formatter import InputFormatter


class Agent:
    previous_reward = 0
    previous_action = 0
    previous_score = 0
    previous_enemy_goals = 0
    previous_owngoals = 0
    def __init__(self, name, team, index):
        self.index = index
        self.inp = InputFormatter(team, index)
        config = tf.ConfigProto(
            device_count={'GPU': 0}
        )
        self.sess = tf.Session(config=config)
        optimizer = tf.train.AdamOptimizer(learning_rate=1e-4)
        writer = tf.summary.FileWriter('tmp/{}-experiment'.format(random.randint(0, 1000000)))
        throttle = np.arange(-1, 1, 1)
        steer = np.arange(-1, 1, 1)
        pitch = np.arange(-1, 1, 1)
        yaw = np.arange(-1, 1, 1)
        roll = np.arange(-1, 1, 1)
        jump = [True, False]
        boost = [True, False]
        handbrake = [True, False]
        option_list = [throttle, steer, pitch, yaw, roll, jump, boost, handbrake]
        self.options = list(itertools.product(*option_list))
        self.state_dim = 193
        self.num_actions = len(self.options)
        print ('num_actions', self.num_actions)
        self.pg_reinforce = PolicyGradientActorCritic(self.sess,
                                                      optimizer,
                                                      self.actor_network,
                                                      self.critic_network,
                                                      self.state_dim,
                                                      self.num_actions,
                                                      summary_writer=writer)

        no_reward_since = 0

        episode_history = deque(maxlen=100)

    def actor_network(self, states):
        # define policy neural network
        W1 = tf.get_variable("W1", [self.state_dim, 20],
                             initializer=tf.random_normal_initializer())
        b1 = tf.get_variable("b1", [20],
                             initializer=tf.constant_initializer(0))
        h1 = tf.nn.tanh(tf.matmul(states, W1) + b1)
        W2 = tf.get_variable("W2", [20, self.num_actions],
                             initializer=tf.random_normal_initializer(stddev=0.1))
        b2 = tf.get_variable("b2", [self.num_actions],
                             initializer=tf.constant_initializer(0))
        p = tf.matmul(h1, W2) + b2
        return p

    def critic_network(self, states):
        # define policy neural network
        W1 = tf.get_variable("W1", [self.state_dim, 20],
                             initializer=tf.random_normal_initializer())
        b1 = tf.get_variable("b1", [20],
                             initializer=tf.constant_initializer(0))
        h1 = tf.nn.tanh(tf.matmul(states, W1) + b1)
        W2 = tf.get_variable("W2", [20, 1],
                             initializer=tf.random_normal_initializer())
        b2 = tf.get_variable("b2", [1],
                             initializer=tf.constant_initializer(0))
        v = tf.matmul(h1, W2) + b2
        return v

    def get_reward(self, packet):
        reward = 0
        score = packet.gamecars[self.index].Score.Score
        diff = score - self.previous_score
        self.previous_score = score
        reward += diff / 100.0 # max per frame is 100, from a goal, normalizes it
        enemy_index = 1 if self.index == 0 else 1
        if (self.previous_enemy_goals - packet.gamecars[enemy_index].Score.Goals) or (self.previous_owngoals - packet.gamecars[self.index].Score.OwnGoals):
            reward -= 1.0
        return reward

    def get_output_vector(self, game_tick_packet):
        state = self.inp.create_input_array(game_tick_packet)
        if self.state_dim != len(state):
            print ('wrong input size', self.index, len(state))
            return self.options[0] # do not return anything
        reward = self.get_reward(game_tick_packet)
        self.pg_reinforce.store_rollout(state, self.previous_action, reward)

        action = self.pg_reinforce.sampleAction(np.array(state).reshape((1, -1)))
        if random.random() < 0.05:
            action = random.randint(0, self.num_actions)
            if action == 256:
                print('f_in rand int', action)
        self.previous_action = action
        if action >= self.num_actions or action < 0:
            print (action, len(self.options))
            return self.options[0]
        return self.options[action]
