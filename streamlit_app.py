import streamlit as st
from scheduler_functions import assign_rooms_to_requests, rooms
from datetime import datetime, timedelta
import pandas as pd

room_types = ["THEATRE", "RECEPTION", "BANQUET", "CLASSROOM", "BOARDROOM", "USHAPE", "HOLLOWSQUARE", "CRESCENT_ROUND"]
# Inject custom CSS to reduce the font size of the multiselect options
st.markdown("""
    <style>
    .stMultiSelect div[role="listbox"] div {
        font-size: 12px;
    }
    .stMultiSelect div[role="listbox"] {
        max-height: 200px;
    }
    </style>
    """, unsafe_allow_html=True)

# Function to create a room request input form
def create_room_request_form(index):
    st.write(f"Room Request {index + 1}")
    
    # First row: Rooms to consider
    rooms_to_consider = st.multiselect(
        f"Rooms to Consider {index + 1}", 
        [room["name"] for room in rooms], 
        default=[room["name"] for room in rooms], 
        key=f"rooms_{index}",
        help="Select the rooms to consider for this request"
    )
    
    # Second row: Other fields
    cols = st.columns(5)
    with cols[0]:
        request_type = st.selectbox(f"Type {index + 1}", room_types, key=f"type_{index}")
    with cols[1]:
        num_people = st.number_input(f"People {index + 1}", min_value=1, key=f"num_people_{index}")
    with cols[2]:
        # Default to tomorrow's date at 9:00
        default_start_date = datetime.now() + timedelta(days=1)
        start_date = st.date_input(f"Start Date {index + 1}", value=default_start_date, key=f"start_date_{index}")
        start_time = st.time_input(f"Start Time {index + 1}", value=datetime.strptime("09:00", "%H:%M").time(), key=f"start_time_{index}")
    with cols[3]:
        # Default to tomorrow's date at 10:00
        default_end_date = datetime.now() + timedelta(days=1)
        end_date = st.date_input(f"End Date {index + 1}", value=default_end_date, key=f"end_date_{index}")
        end_time = st.time_input(f"End Time {index + 1}", value=datetime.strptime("10:00", "%H:%M").time(), key=f"end_time_{index}")

    start_datetime = datetime.combine(start_date, start_time).strftime("%Y-%m-%d %H:%M")
    end_datetime = datetime.combine(end_date, end_time).strftime("%Y-%m-%d %H:%M")
    
    return {
        "type": request_type, 
        "num_rooms": 1, 
        "num_people": num_people, 
        "time_slots": [[start_datetime, end_datetime]], 
        "rooms_to_consider": rooms_to_consider
    }

# Streamlit app
st.title("Room Request Scheduler")

# Ask for the number of room requests
num_requests = st.number_input("Enter the Number of Room Requests", min_value=1, step=1)

# Create input forms for each room request
requests = []
for i in range(num_requests):
    request = create_room_request_form(i)
    requests.append(request)

# Display the collected requests
if st.button("Submit"):
    # Call the function to solve the problem
    resolved_solutions = assign_rooms_to_requests(rooms, requests, floor_weight=1, space_weight=0.5)
    df_solutions = pd.DataFrame(resolved_solutions)
    df_solutions_show= df_solutions.copy()
    df_solutions_show = df_solutions_show[['request_no','time_slot','room_name','room_rental']]
    df_solutions_show = df_solutions_show.sort_values(by=['request_no'], ascending=True)

    # Format room_rental as currency
    df_solutions_show['room_rental'] = df_solutions_show['room_rental'].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else x)
    st.dataframe(df_solutions_show)
    
    # Example usage of the collected requests
    # You can replace this with your actual function call
    # assign_rooms_to_requests(rooms, requests, floor_weight=1, space_weight=0.5)