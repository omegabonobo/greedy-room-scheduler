from ortools.linear_solver import pywraplp
from datetime import datetime
import csv

rooms = []
with open('IHG_Montreal_Rooms.csv') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        room = {}
        room["name"] = row["ROOM_NAME"]
        room["type_capacity"] = {key.split("_")[1]: int(row[key]) if row[key].isdigit() else 0 for key in row if key.startswith("CAPACITY_")}
        room["floor"] = int(row["FLOOR"]) if row["FLOOR"].isdigit() else 0
        rooms.append(room)

def assign_rooms_to_requests(rooms, requests, floor_weight=1, space_weight=1, reuse_weight=1):
    # Helper function to check if two time slots overlap
    def timeslot_overlap(ts1, ts2):
        # Convert string time slots to datetime objects
        start1, end1 = [datetime.strptime(ts, "%Y-%m-%d %H:%M") for ts in ts1]
        start2, end2 = [datetime.strptime(ts, "%Y-%m-%d %H:%M") for ts in ts2]
        
        # Check if there is an overlap
        return not (end1 <= start2 or end2 <= start1)

    # Initialize the solver
    solver = pywraplp.Solver.CreateSolver('SCIP')

    # Room assignment variables
    room_vars = {}

    # Define valid rooms for each request
    valid_rooms_for_request = {}

    # Define room assignment variables based on request and time slot overlap
    for r_id, room in enumerate(rooms):
        for req_id, request in enumerate(requests):
            for t_id, time_slot in enumerate(request['time_slots']):
                # Check if room meets request's capacity
                if request["type"] in room["type_capacity"] and room["type_capacity"][request["type"]] >= request["num_people"]:
                    # Define the room assignment variable for this request, room, and time slot
                    room_vars[(r_id, req_id, t_id)] = solver.BoolVar(f"room_{r_id}_req_{req_id}_time_{t_id}")
                    
                    # Collect valid rooms for the current request (based on capacity and time slot)
                    if req_id not in valid_rooms_for_request:
                        valid_rooms_for_request[req_id] = []
                    valid_rooms_for_request[req_id].append(room_vars[(r_id, req_id, t_id)])

    # Debugging: Print the valid rooms for each request
    for req_id in valid_rooms_for_request:
        valid_room_names = []
        for room_var in valid_rooms_for_request[req_id]:
            r_id, req_id, t_id = room_var.name().split('_')[1], room_var.name().split('_')[3], room_var.name().split('_')[5]
            valid_room_names.append(rooms[int(r_id)]["name"])  # Get room name based on id
        print(f"Available rooms for request {req_id}: {valid_room_names}")

    # Add constraint: each request can only be assigned one room at a time
    for req_id, valid_rooms in valid_rooms_for_request.items():
        solver.Add(solver.Sum(valid_rooms) == 1)

    # Add constraint: each room can only be assigned to one request at a time for overlapping time slots
    for r_id, room in enumerate(rooms):
        for req_id1, request1 in enumerate(requests):
            for t_id1, time_slot1 in enumerate(request1["time_slots"]):
                for req_id2, request2 in enumerate(requests):
                    if req_id1 != req_id2:
                        for t_id2, time_slot2 in enumerate(request2["time_slots"]):
                            if timeslot_overlap(time_slot1, time_slot2):
                                if (r_id, req_id1, t_id1) in room_vars and (r_id, req_id2, t_id2) in room_vars:
                                    solver.Add(room_vars[(r_id, req_id1, t_id1)] + room_vars[(r_id, req_id2, t_id2)] <= 1)

    # Define the floor distance, unused space, and reuse terms
    distance_terms = []
    unused_space_terms = []
    reuse_terms = []

    for r_id, room in enumerate(rooms):
        for req_id, request in enumerate(requests):
            for t_id, time_slot in enumerate(request['time_slots']):
                if (r_id, req_id, t_id) in room_vars:
                    # Calculate the floor distance as absolute difference between floors
                    for other_r_id, other_room in enumerate(rooms):
                        if other_r_id != r_id and (other_r_id, req_id, t_id) in room_vars:
                            floor_distance = abs(room["floor"] - other_room["floor"])
                            # Create an auxiliary variable for the product of two boolean variables
                            aux_var = solver.BoolVar(f"aux_{r_id}_{other_r_id}_{req_id}_{t_id}")
                            solver.Add(aux_var <= room_vars[(r_id, req_id, t_id)])
                            solver.Add(aux_var <= room_vars[(other_r_id, req_id, t_id)])
                            solver.Add(aux_var >= room_vars[(r_id, req_id, t_id)] + room_vars[(other_r_id, req_id, t_id)] - 1)
                            distance_terms.append(aux_var * floor_distance * floor_weight)

                    # Calculate unused space (room capacity - number of people)
                    unused_space = room["type_capacity"][request["type"]] - request["num_people"]
                    unused_space_terms.append(room_vars[(r_id, req_id, t_id)] * unused_space * space_weight)

                    # Add reuse term to favor reusing rooms
                    reuse_terms.append(room_vars[(r_id, req_id, t_id)] * reuse_weight)

    # Add an objective function to minimize the floor distance, unused space, and favor reusing rooms
    solver.Minimize(solver.Sum(distance_terms) + solver.Sum(unused_space_terms) - solver.Sum(reuse_terms))

    # Solve the problem
    status = solver.Solve()

    # Store the final solutions
    solutions = []
    if status == pywraplp.Solver.OPTIMAL:
        print("Solution found:")
        for r_id, req_id, t_id in room_vars:
            if room_vars[(r_id, req_id, t_id)].solution_value() == 1:
                solution = {
                    "request_id": req_id,
                    "room_name": rooms[r_id]['name'],
                    "time_slot": requests[req_id]['time_slots'][t_id]
                }
                solutions.append(solution)
                print(f"Request {req_id} assigned to Room {rooms[r_id]['name']} for time slot {requests[req_id]['time_slots'][t_id]}")
    else:
        print("No solution found.")

    # Return the final solutions
    return solutions