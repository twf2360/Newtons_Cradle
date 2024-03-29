import math
import numpy as np 
from ball import ball
import matplotlib.pyplot as plt 
import copy
import matplotlib.animation as animation
from itertools import combinations
import sys
import pandas as pd
from time import time
import os
g_scalar = 9.81
g_vector = np.array([0,-9.81])
system_states_to_plot = []
np.seterr(over='raise')
class calculator:
    '''

    A class used to calculate the motion of the ball, save the movement of the balls to disk so that they can later be read in
    
    takes the number of iterations, and the timesteps between iterations as arguments
    uses the ball class to define ball objects.

    '''

    def __init__(self, timestep, iterations):
        '''
        initalistation function of the class 
        timestep = the difference in time between the updates of the balls position
        iterations = the number of timesteps ran through

        the attribute ball list is also created at this point. Though currently empty, it will be filled with ball objects when the "get balls" function is used
        '''
        self.timestep = timestep
        self.iterations = iterations 
        self.ball_list = []
        system_states_to_plot.clear() #when the class is called upon multiple times by main.py, this ensures there is not overlapping data between systems
        
        
       
    


    def get_balls(self, number, positions, velocities, radii, masses, anchors):
        '''
        fills the ball list attribute with balls that are defined using the inputs to this function
        
        inputs:
        number = number of balls (int)
        positions = starting position of all of the balls (array_like)
        velocities = starting velocities of all of the balls (array_like)
        radii = radii of all of the balls (array_like)
        masses = mass of all of the balls (array_like)
        anchors = anchor points for all of the balls (array_like)
        '''
        self.number = number
        
        for i in np.arange(self.number): #generate the correct number of balls 
            spawnedBall = ball(position= np.array(positions[i], dtype = float),velocity= np.array(velocities[i], dtype = float), radius= np.array(radii[i], dtype = float), mass = masses[i], anchor= anchors[i])
            self.ball_list.append(spawnedBall) #add the newly create ball object into the list of all balls in the system
        
        
        return self.ball_list



    
    def fluid_resistance(self, ball, density):
        ''' 
        calculates the force due to fluid resistance on the ball.
        
        inputs: 
        ball - ball object which is moving throug the fluid (ball)
        density - the density of the fluid the ball is moving through in kg/m^3 (float)

        

        returns array_like object that is the vector force due to fluid resistance
        '''
        fluid_density = density 
        
        drag_coefficient = 0.5 #just googled the drag co-efficent of a sphere
        
        cross_sec_area = math.pi * ball.radius**2
        
        if not np.any(ball.velocity): #if the ball has no velocity then the fluid resistance is 0
            return [0,0] 
        
        velocity = ball.velocity
        speed = np.linalg.norm(velocity)
        
        vel_direction = velocity / speed

        force_scalar = 0.5 * fluid_density * speed**2 *drag_coefficient * cross_sec_area #calculate magnitude of drag force
        force_vector = (-force_scalar) * vel_direction # - as it always acts against the direction of the velocity
        return force_vector

    def collision(self, ball1, ball2):
        '''
        calculates the change in velocities if there's a collision, and updates the velocities of the ball objects
        the change is velocities is calculated by the conservation of energy and momentum, and therefore assumes perfectly elastic collisions
        
        inputs :
        two ball objects, ball1 and ball2 that are colliding
        ball objects are defined to be colliding if ball.overlap returns True

        
        '''
        totalMass = ball1.mass + ball2.mass

        pos1, pos2 = ball1.position, ball2.position
        distance = np.linalg.norm(pos1 - pos2)**2 #distance between the two balls
        v1_before = ball1.velocity #velocity of ball 1 before the collision
        v2_before = ball2.velocity # #velocity of ball 2 before the collision


        v1_after = v1_before - (2*ball1.mass / totalMass) * (np.dot((v1_before-v2_before), (pos1- pos2)) / distance) * (pos1 - pos2) #derived from consv. of KE and momentum
        v2_after = v2_before - (2*ball2.mass / totalMass) * (np.dot((v2_before-v1_before) ,(pos2- pos1)) / distance) * (pos2 - pos1)


        
        ''' as mentioned in report, there is a section where the y velocity after collisions was artificially set to zero. 

        
        v1_y = 0
        v2_y = 0

        although not used, this is kept here for reference     
        '''


        v1_x = v1_after[0]
        v2_x = v2_after[0] 
        
        v1_y = v1_after[1]
        v2_y = v2_after[1]
        
        ball1.velocity = np.array([v1_x, v1_y], dtype= float) #change the ball velocities to the new, calculated velocities
        ball2.velocity = np.array([v2_x, v2_y], dtype = float)

    def stringtension(self,ball):
        ''' 
        calculates the force on the ball due to the string tension
        
        input: 
        ball - a ball object
    

        returns array_like object that is the vector force of the string tension
        '''
        magAcceleration = (np.linalg.norm(ball.velocity)**2)/ball.length #calculate magnitude of  centripetal acceleration

        delta_x = np.abs((ball.position[0] - ball.anchor[0])) #difference in x co-ordinate between balls position and anchor point
        delta_y = np.abs((ball.position[1] - ball.anchor[1])) #difference in y co-ordinate between balls position and anchor point

        to_anchor = ball.anchor - ball.position  # the vector that defines the string from the ball to the anchor
        normalisation = np.linalg.norm(to_anchor) # the length of the string - could use ball.length here??
        
        
        if (not np.isnan(delta_x)) and (delta_x != 0) and (not np.isnan(delta_y)) and (delta_y != 0):
            ''' this to avoid the possibility of any divide by 0 errors within the tan if the ball is at 0 or 90 degrees to the vertical '''
            angPos = math.atan(delta_x/delta_y) #angle of the ball compared to the anchor
        
        elif (np.isnan(delta_y)) or (delta_y == 0):
            angPos = (math.pi/2)
        
        else:
            angPos = 0
        
        stringTension_scalar = ((ball.mass*g_scalar*math.cos(angPos)) + ball.mass*magAcceleration) #calculate magnitude of string tension
        stringTension_vector = stringTension_scalar * (np.array((to_anchor)/normalisation)) #times magnitude by the direction of string tension force 

        return stringTension_vector

    def calculate_acceleration(self, ball, density):
        '''
        calculate the acceleration of the ball if there is no collision

        inputs:
        ball - ball object for which the acceleration is to be calculated
        density - the fluid density through which the ball is moving in kg/m^3 (float)
        
        returns the acceleration of the ball object that was inputted
        '''
        tension_force = self.stringtension(ball) #calculates the string tension force

        air_resistance_force = self.fluid_resistance(ball, density) #calculates the fluid resistance force


        netForce = ball.mass*g_vector + tension_force + air_resistance_force #add the forces together to calculate net force 
        acceleration = (netForce/ball.mass) #newtons second law to calculate acceleratiob
        return acceleration
        


    def calculate(self, approximation, density):
        time_and_balls = []
        '''
        calculate the movement of the ball, with a chosen approximation

        inputs:
        approximation - the approximation used to model the motion, corresponding to an update function within ball.py (str)
        desnity - the fluid density through which the ball is moving in kg/m^3 (float)

        saves 'system_states_over_time.npy' to disk, which is the ball objects list, time, approximation, and density, for every timestep
        returns collision_info, an array of all of the points in time at which there was a collision
        '''
        collision_info = [] #make the list that will be read later by the dataframes class. This list willcontain collision info, and basic system parameters 
        fluid_density = density
        collision_info.append([self.timestep ,approximation, fluid_density]) #add the system parameters
        
        if not approximation.lower() in ('cromer', 'euler', 'rk2'): #ensure the approximation is a recognised one. 
            print('approximation not recognised, must be cromer, euler, or RK2')
            sys.exit()
        
        constant_collisions = 0 #this value is set to nonzero when the balls are found to be stationary, therefore constantly colliding - could use true / false instead 
        for i in np.arange(self.iterations): # needs to be calculated every iteration
            for ball in self.ball_list: #balls movement is calculated individually
                while True:
                    pairs = combinations(range(self.number), 2) #split the balls up into bairs to test if they're overlapping 
                    for x,y in pairs:
                        if self.ball_list[x].overlap(self.ball_list[y]): #if the balls are colliding
                            
                            if (np.isclose(self.ball_list[x].velocity, [0,0], atol=0.0005).all()) and (np.isclose(self.ball_list[y].velocity, [0,0], atol=0.0005).all()): #the balls will be found to be constantly coliding if stationary
                                self.collision(self.ball_list[x], self.ball_list[y]) 
                                if constant_collisions == 0:
                                    collision_info.append('stationary balls, constant collisions') 
                                    constant_collisions += 1
                                break 
                            
                            #print('There was a collsison at iteration {}'.format(i))

                          
                            self.collision(self.ball_list[x], self.ball_list[y])
                            
                            number = i + 1
                            collision_info.append('iteration {}, time {}s'.format(number, self.timestep*number)) #add the details of the collision to the collision info list for the dataframe

                            break
                    
                    
                    acceleration = self.calculate_acceleration(ball, fluid_density) #if there's no collision, just calculate the normal pendulum acceleration
                    delta_v = acceleration * self.timestep  # calculate the change in velocity over the timestep
                    
                    break   
                
                ''' use the selected approximation, automatically set to lower case to avoid them not being recognised due to casing '''
                if approximation.lower() == 'euler':
                    ball.euler_update(delta_v, self.timestep)
                
                if approximation.lower() == 'cromer':
                    ball.cromer_update(delta_v, self.timestep) 
                
                if approximation.lower() == 'rk2':
                    start_points = ball.runge_kutta2_prep(acceleration, self.timestep)
                    start_position = start_points[0]
                    start_velocity = start_points[1]
                
                    mid_acceleration = self.calculate_acceleration(ball, density)

                    ball.runge_kutta2(start_position, start_velocity, acceleration, mid_acceleration, self.timestep)
                
            ''' add the time, and the state of the system - all of the ball objects in their current state - to a list that will be read in by the plotter '''
            time = (i+1) * self.timestep
            time_and_balls = [time, copy.deepcopy(self.ball_list)]
            system_states_to_plot.append(time_and_balls)

        if os.path.isfile('system_states_over_time.npy'): #  if the data of the simulation already exists, this will be from a previous version, and must be deleted
            os.remove('system_states_over_time.npy')
        
        np.save('system_states_over_time.npy', system_states_to_plot, allow_pickle=True) #save the state of the system over time to disk so it can be used by plotter
        return collision_info

    def time_to_run(self, approximation, density):
        '''
        used to return the time to run the calculate function, as well as the collision info
        
        requires all of the same inputs as the calculate function

        '''
        start_time = time() #time before doing the calculation 
        collision_info = self.calculate(approximation, density)
        time_to_run = time() - start_time #ttotal time take to run the calculation
        return [time_to_run, collision_info]



        
