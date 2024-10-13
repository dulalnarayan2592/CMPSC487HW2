# Import all necessary kivy components
from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.popup import Popup
from datetime import datetime, timedelta

import firebase_admin
from firebase_admin import credentials, firestore

# **Database Initialization**
database_json_path = 'reservation-4cf02-firebase-adminsdk-5l5ky-2703738411.json'
credentail = credentials.Certificate(database_json_path)
firebase_admin.initialize_app(credentail)
database = firestore.client()

# **Function to retrieve all reservations from Firestore**
def retrieve_reservation():
    return database.collection('Reservations').get()

# **Function to check conflicting reservations**
def check_conflicting_reservations(car_type, new_date):
    reservations = retrieve_reservation()
    for reservation in reservations:
        data = reservation.to_dict()
        reservation_date = data['reservation_date'].replace(tzinfo=None)
        if data['car_type'] == car_type and reservation_date >= new_date:
            return True  # Conflict found
    return False  # No conflicts

# **Function to update the return date**
def update_return_date(reservation_id, new_return_date):
    database.collection('Reservations').document(reservation_id).update({'return_date': new_return_date})

# **Function to update the reservation status**
def update_reservation_status(reservation_id, status):
    database.collection('Reservations').document(reservation_id).update({'status': status})

# **Function to display popups**
def show_popup(title, message):
    layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
    label = Label(text=message)
    close_button = Button(text="Close", size_hint=(1, 0.25))
    layout.add_widget(label)
    layout.add_widget(close_button)
    popup = Popup(title=title, content=layout, size_hint=(0.6, 0.4))
    close_button.bind(on_press=popup.dismiss)
    popup.open()

# **Reservation Form Screen**
class ReservationForm(Screen):
    def __init__(self, **kwargs):
        super(ReservationForm, self).__init__(**kwargs)
        self.build_form()  # Build the form on initialization

    # **Function to build the reservation form layout**
    def build_form(self):
        layout = GridLayout(cols=2, padding=20, spacing=10)

        layout.add_widget(Label(text="Driver's Name:"))
        self.name_input = TextInput()
        layout.add_widget(self.name_input)

        layout.add_widget(Label(text="Reservation Date (MM-DD-YYYY):"))
        self.date_input = TextInput()
        layout.add_widget(self.date_input)

        layout.add_widget(Label(text="Reservation Time (HH:MM):"))
        self.time_input = TextInput()
        layout.add_widget(self.time_input)

        layout.add_widget(Label(text="Return Date (MM-DD-YYYY):"))
        self.return_date_input = TextInput()
        layout.add_widget(self.return_date_input)

        layout.add_widget(Label(text="Car Type:"))
        self.car_type_spinner = Spinner(
            text='Select Car Type',
            values=('Sedan', 'SUV', 'Pick-up', 'Van')
        )
        layout.add_widget(self.car_type_spinner)

        layout.add_widget(Label(text="Request Extension:"))
        self.extension_spinner = Spinner(text='No', values=('No', 'Yes'))
        layout.add_widget(self.extension_spinner)

        layout.add_widget(Label(text="New Return Date (MM-DD-YYYY):"))
        self.new_return_date_input = TextInput()
        layout.add_widget(self.new_return_date_input)

        # **Submit and Admin View buttons**
        submit_button = Button(text="Submit", on_press=self.submit_reservation)
        layout.add_widget(submit_button)

        admin_button = Button(text="Admin View", on_press=self.go_to_admin)
        layout.add_widget(admin_button)

        # **Add the layout to the screen**
        self.add_widget(layout)

    # **Function to handle reservation submission**
    def submit_reservation(self, instance):
        # **Get user inputs**
        name = self.name_input.text
        car_type = self.car_type_spinner.text
        date = self.date_input.text
        time = self.time_input.text
        return_date = self.return_date_input.text

        # **Validate required fields**
        if not name or car_type == 'Select Car Type' or not date or not time or not return_date:
            show_popup("Error", "Please fill in all fields.")
            return

        # **Validate date/time format**
        try:
            reservation_datetime = datetime.strptime(f"{date} {time}", '%m-%d-%Y %H:%M')
            return_datetime = datetime.strptime(f"{return_date} {time}", '%m-%d-%Y %H:%M')
        except ValueError:
            show_popup("Error", "Invalid date/time format.")
            return

        # **Check if reservation is at least 24 hours in advance**
        if reservation_datetime - datetime.now() < timedelta(hours=24):
            show_popup("Error", "Reservations must be made at least 24 hours in advance.")
            return

        # **Add reservation to Firestore**
        database.collection('Reservations').add({
            'name': name,
            'car_type': car_type,
            'reservation_date': reservation_datetime,
            'return_date': return_datetime,
            'status': 'Pending'
        })
        show_popup("Success", f"Reservation made for {name}.")

    # **Navigate to Admin View**
    def go_to_admin(self, instance):
        self.manager.current = 'admin_view'

# **Admin View Screen**
class AdminView(Screen):
    def __init__(self, **kwargs):
        super(AdminView, self).__init__(**kwargs)
        self.build_admin_view()

    # **Function to build the admin view layout**
    def build_admin_view(self):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        title_label = Label(
            text="Mr. Johnson's Reservation List",
            font_size=24, size_hint=(1, None), height=50,
            halign='center', valign='middle'
        )
        title_label.bind(size=title_label.setter('text_size'))
        layout.add_widget(title_label)

        # **Scrollable view for reservations**
        scroll_view = ScrollView(size_hint=(1, 1))
        self.reservations_layout = GridLayout(cols=1, size_hint_y=None, spacing=20, padding=20)
        self.reservations_layout.bind(minimum_height=self.reservations_layout.setter('height'))
        scroll_view.add_widget(self.reservations_layout)
        layout.add_widget(scroll_view)

        # **Refresh and Back buttons**
        buttons_layout = BoxLayout(orientation='horizontal', size_hint=(1, None), height=60)
        refresh_button = Button(text="Refresh Reservations", size_hint=(0.5, 1))
        refresh_button.bind(on_press=self.view_reservations)

        back_button = Button(text="Back to Reservation Form", size_hint=(0.5, 1))
        back_button.bind(on_press=self.go_to_form)

        buttons_layout.add_widget(refresh_button)
        buttons_layout.add_widget(back_button)
        layout.add_widget(buttons_layout)

        self.add_widget(layout)

    # **Function to display reservations**
    def view_reservations(self, instance):
        self.reservations_layout.clear_widgets()
        reservations = retrieve_reservation()

        for reservation in reservations:
            data = reservation.to_dict()
            details = (
                f"Name: {data['name']}\n"
                f"Car Type: {data['car_type']}\n"
                f"Reservation Date: {data['reservation_date'].strftime('%m-%d-%Y @ %H:%M')}\n"
                f"Return Date: {data['return_date'].strftime('%m-%d-%Y @ %H:%M')}\n"
                f"Status: {data['status']}"
            )
            reservation_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=200, padding=10, spacing=10)
            details_label = Label(text=details, size_hint_y=None, height=100)
            reservation_box.add_widget(details_label)

            buttons_layout = BoxLayout(orientation='vertical', size_hint=(0.3, 1), spacing=10)
            approve_button = Button(text="Approve", on_press=lambda btn, res_id=reservation.id: self.update_reservation(res_id, 'Approved'))
            deny_button = Button(text="Deny", on_press=lambda btn, res_id=reservation.id: self.update_reservation(res_id, 'Denied'))
            buttons_layout.add_widget(approve_button)
            buttons_layout.add_widget(deny_button)
            reservation_box.add_widget(buttons_layout)
            self.reservations_layout.add_widget(reservation_box)

    # **Update reservation status**
    def update_reservation(self, reservation_id, status):
        update_reservation_status(reservation_id, status)
        self.view_reservations(None)

    # **Navigate to the Reservation Form screen**
    def go_to_form(self, instance):
        self.manager.current = 'reservation_form'

# **RentalApp Class: Main Kivy App**
class RentalApp(App):
    # Function to build the application
    def build(self):
        sm = ScreenManager()  # Initialize the ScreenManager

        # Add ReservationForm and AdminView screens to the ScreenManager
        sm.add_widget(ReservationForm(name='reservation_form'))
        sm.add_widget(AdminView(name='admin_view'))

        return sm  # Return the ScreenManager as the root widget

# **Entry point of the application**
if __name__ == '__main__':
    RentalApp().run()  # Start the Kivy app
