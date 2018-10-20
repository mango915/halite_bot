#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#!C:\Users\Utente\Anaconda3 python
# Import the Halite SDK, which will let you interact with the game.
import hlt
from hlt import constants
import random
import logging

# This game object contains the initial game state.
game = hlt.Game()

#my functions
def spawn_ship_cond(me, game, game_map, N, D):
    if (me.halite_amount >= constants.SHIP_COST + 500*N +10*game.turn_number and 
    game.turn_number < constants.MAX_TURNS - 75 and not 
    game_map[me.shipyard].is_occupied) :
        return True
    else:
        return False

def make_drop_cond(ship, me, game, game_map, N, D):
    T = False
    if (me.halite_amount >= constants.DROPOFF_COST + 2000*(D**2) and
        count_hlt(ship.position) > constants.MAX_HALITE and
        ship.halite_amount > constants.MAX_HALITE/2 and
        game.turn_number < constants.MAX_TURNS - 100 and
        game_map.calculate_distance(ship.position, me.shipyard.position) > 7):
        T = True
    return T
        
def choose_dir_exp(ship, me, game_map, dangerous_pos):
    danger_p = []
    for k in dangerous_pos.keys():
        if k != ship.id:
            danger_p = danger_p + dangerous_pos[k]  
    v = []
    dirs = hlt.Direction.get_all_cardinals()
    for d in dirs:
        p = ship.position.directional_offset(d)
        h = game_map[p].halite_amount
        if p not in danger_p:
            v.append((d,p,h))
        else:
            continue    
    p = ship.position
    d = hlt.Direction.Still
    h = game_map[p].halite_amount
    #if p not in danger_p:
    v.append((d,p,h))     
    index = 0
    h_max = 0
    for i in range(len(v)):
        if v[i][2] > h_max:
            h_max = v[i][2]
            index = i
        else:
            continue
    if h_max > 2.15*v[-1][2]:
        best_dir = v[index][0]
    else:
        best_dir = v[-1][0]
    #logging.info("Chosen direction: {}.".format(best_dir ))
    return best_dir 

def count_hlt (position):
    h = game_map[position].halite_amount
    pos = position.get_surrounding_cardinals()
    for p in pos:
        h = h + game_map[p].halite_amount
    return h 

def check_ships_status(status):
    T = False
    for k in ship_status:
        if ship_status[k][0] == status:
            T = True
            break
        else:
            continue
    return T
    
ship_status = {}
drop_status = {}
# Respond with your name.
game.ready("ND96_bot")

while True:
    game.update_frame()
    me = game.me
    game_map = game.game_map
    logging.info("Halite available: {}.".format(me.halite_amount))
    N = 0
    D = 0
    command_queue = []
    dangerous_pos = {} 
    free_docks = {}
    #mapping all possible dangerous position
    for ship in me.get_ships():
        dangerous_pos[ship.id] = ship.position.get_surrounding_cardinals()
        dangerous_pos[ship.id].append(ship.position)
    #listing in a dict all dropoffs
    if me.shipyard.id not in drop_status:
        drop_status[me.shipyard.id] = [me.shipyard.position, "on", 0, count_hlt(me.shipyard.position)]
    for drop in me.get_dropoffs():
        if drop.id not in drop_status:
            # values = [position, status, # of ships assigned, halite around dock]
            drop_status[drop.id] = [drop.position, "on", 0, count_hlt(drop.position)]
        else: 
            continue
    D = len(drop_status) - 1
    logging.info("Number of dropoffs = {}".format(D))
    #ship management - fase 0: update ships labels
    for ship in me.get_ships():  
        #logging.info("Ship {} has {} halite.".format(ship.id, ship.halite_amount))
        map_cell = game_map[ship.position]
        map_cell.mark_unsafe(ship)
        if ship.id not in ship_status:
            #default assignment to avoid bugs
            ship_status[ship.id] = ["exploring", me.shipyard.id]
            for kd in drop_status:
                if drop_status[kd][1] == "on":
                    ship_status[ship.id] = ["exploring", kd]
                    break
                else:
                    continue
                    
        N = len(ship_status)
        if ship_status[ship.id][0] == "returning":
            if (ship.position == drop_status[ship_status[ship.id][1]][0] ):
                #I have to assign also a dock
                ship_status[ship.id][0] = "exploring" 
        #exploring ships
        elif ship.halite_amount >= constants.MAX_HALITE *3 / 4 and ship_status[ship.id][0] == "exploring":
            #I have to assign also a dock
            ship_status[ship.id][0] = "returning"
        #dropoff ships
        elif make_drop_cond(ship, me, game, game_map, N, D) : 
            if (check_ships_status("dropoff") == False and 
            check_ships_status("forced_dropoff") == False): 
                ship_status[ship.id][0] = "dropoff"  
        if D > 0 and ship_status[ship.id][0] not in ["exploring","returning"]:
            logging.info("Ship {} in status {} to dock {}".format(ship.id, ship_status[ship.id][0], ship_status[ship.id][1])) 
            
    #update of the number of ships assigned to each dock and the surrounding halite
    for k in drop_status:
        counts = 0
        for s in ship_status:
            if ship_status[s][1] == k:
                counts = counts + 1
            drop_status[k][2] = counts
            if counts > 10:
                drop_status[k][1] = "crowded"
        drop_status[k][3] = count_hlt(drop_status[k][0])
        if drop_status[k][3] < 10:
            drop_status[k][1] = "off"
        if drop_status[k][1] == "on":
            free_docks[k] = drop_status[k]
        F = len(free_docks)
        logging.info("Dock {} in status {} with {} ships and {} halite.".format(k, drop_status[k][1], drop_status[k][2], drop_status[k][3] ))
        
    #fase 2: give a command to each status
    for ship in me.get_ships():
    
        if ship_status[ship.id][0] == "exploring" and F > 0 and (ship_status[ship.id][1] in ["crowded","off"]) :
            d = 100
            for key in free_docks:
                if game_map.calculate_distance(ship.position,free_docks[key][0]) < d:
                    d = game_map.calculate_distance(ship.position,free_docks[key][0])
                    dk = key
                else: 
                    continue
            ship_status[ship.id][1] = dk
        #logging.info("Ship {} changed to dock {}".format(ship.id, ship_status[ship.id][1] ))
        #@@@ seems ok        
        if ship_status[ship.id][0] == "returning":
            if ship.halite_amount > game_map[ship.position].halite_amount/2:
                #if at least one dropoff has been build
                if D > 0:
                    d = 100
                    for key in drop_status:
                        if game_map.calculate_distance(ship.position,drop_status[key][0]) < d:
                            d = game_map.calculate_distance(ship.position,drop_status[key][0])
                            dk = key
                        else: 
                            continue
                    if  drop_status[dk][1] == "on" : #(d <= game_map.calculate_distance(ship.position, me.shipyard.position)) and
                        ship_status[ship.id][1] = dk
                    #all those situations have to be treated more carefully
                    elif (drop_status[dk][1] == "off" and 
                        check_ships_status("forced_dropoff") == False and
                        check_ships_status("dropoff") == False): #or "crowded"
                        ship_status[ship.id][0] = "forced_dropoff"
                    else:
                        ship_status[ship.id][1] = me.shipyard.id
                    move = game_map.naive_navigate(ship, drop_status[ship_status[ship.id][1]][0])
                    command_queue.append(ship.move(move))
                else:
                    move = game_map.naive_navigate(ship, me.shipyard.position)
                    command_queue.append(ship.move(move))
            else:
                move = hlt.Direction.Still
                command_queue.append(ship.move(move))
        #@@@ seems ok                     
        elif ship_status[ship.id][0] == "dropoff":
            logging.info("Ship {} converted to dropoff".format(ship.id))
            command_queue.append(ship.make_dropoff())
            
        elif ship_status[ship.id][0] == "forced_dropoff":
            if (me.halite_amount >= constants.DROPOFF_COST and not
                game_map[ship.position].has_structure):
                logging.info("Ship {} forced to dropoff".format(ship.id))
                command_queue.append(ship.make_dropoff())
            else:
                 move = hlt.Direction.Still
                 command_queue.append(ship.move(move))
        #command for exploring ships
        else:
            command_queue.append(ship.move(choose_dir_exp(ship, me, game_map, dangerous_pos)))

    # If you have zero ships and have enough halite, spawn a ship.
    # Don't spawn a ship if you currently have a ship at port, though.
    if spawn_ship_cond(me, game, game_map, N, D):
        command_queue.append(game.me.shipyard.spawn())
    
    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)



    

    