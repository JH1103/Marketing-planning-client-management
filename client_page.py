"""Client pages for the Marketing Planning App.

Do not run this file directly. Run main_menu.py.
"""
import re
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_PATTERN = re.compile(r"^\d{9,10}$")
MIN_PASSWORD_LENGTH = 8
MAX_NAME_LENGTH = 50
MAX_COMPANY_LENGTH = 50
MAX_INDUSTRY_LENGTH = 50
MAX_NOTES_LENGTH = 300
MAX_PURPOSE_LENGTH = 150
OTP_VALID_SECONDS = 300
PASSWORD_REQUIREMENTS_MSG = (
    f"Password must be at least {MIN_PASSWORD_LENGTH} characters long "
    "and contain at least one letter and one number."
)

def is_valid_email(value):
    return bool(EMAIL_PATTERN.match(value))

def is_valid_phone(value):
    return bool(PHONE_PATTERN.match(value))

def is_valid_password(value):
    return (len(value) >= MIN_PASSWORD_LENGTH
            and any(c.isalpha() for c in value)
            and any(c.isdigit() for c in value))


class ClientPageMixin:
    def show_forgot_password_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Forgot Password")
        dialog.geometry("420x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Reset Password", style='Title.TLabel').pack(pady=10)
        
        container = ttk.Frame(dialog)
        container.pack(fill='both', expand=True, padx=20, pady=10)
        
        def clear_container():
            for w in container.winfo_children():
                w.destroy()
        
        def build_step_email():
            clear_container()
            ttk.Label(container, text="Enter your registered email:").pack(pady=(10, 5))
            email_entry = ttk.Entry(container, width=35)
            email_entry.pack(pady=5)
            email_entry.focus_set()
            
            def send_otp():
                email = email_entry.get().strip()
                if not email:
                    messagebox.showerror("Error", "Please enter your email.")
                    return
                
                otp, error = self.profile_manager.request_password_reset(email)
                if error:
                    messagebox.showerror("Error", error)
                    return
                
                # No real mail server in this demo, so the OTP is shown
                # directly instead of actually being emailed.
                messagebox.showinfo(
                    "OTP Sent",
                    f"An OTP has been sent to {email}.\n\n"
                    f"(Demo mode - your OTP is: {otp})\n\n"
                    f"It is valid for {OTP_VALID_SECONDS // 60} minutes."
                )
                build_step_otp(email)
            
            ttk.Button(container, text="Send OTP", command=send_otp).pack(pady=15)
            email_entry.bind('<Return>', lambda e: send_otp())
        
        def build_step_otp(email):
            clear_container()
            ttk.Label(container, text=f"Enter the OTP sent to {email}:").pack(pady=(5, 5))
            otp_entry = ttk.Entry(container, width=20)
            otp_entry.pack(pady=5)
            otp_entry.focus_set()
            
            pw_frame = ttk.Frame(container)
            pw_frame.pack(pady=10)
            
            ttk.Label(pw_frame, text="New Password:").grid(row=0, column=0, sticky='w', pady=3, padx=5)
            new_pw_entry = ttk.Entry(pw_frame, width=25, show='*')
            new_pw_entry.grid(row=0, column=1, pady=3, padx=5)
            self._add_show_password_toggle(pw_frame, new_pw_entry, row=0, column=2)
            
            ttk.Label(pw_frame, text="Confirm Password:").grid(row=1, column=0, sticky='w', pady=3, padx=5)
            confirm_pw_entry = ttk.Entry(pw_frame, width=25, show='*')
            confirm_pw_entry.grid(row=1, column=1, pady=3, padx=5)
            self._add_show_password_toggle(pw_frame, confirm_pw_entry, row=1, column=2)
            
            def do_reset():
                otp_entered = otp_entry.get().strip()
                new_password = new_pw_entry.get().strip()
                confirm_password = confirm_pw_entry.get().strip()
                
                if not otp_entered or not new_password or not confirm_password:
                    messagebox.showerror("Error", "Please fill in all fields.")
                    return
                if new_password != confirm_password:
                    messagebox.showerror("Error", "Passwords do not match.")
                    return
                
                success, msg = self.profile_manager.verify_otp_and_reset(email, otp_entered, new_password)
                if not success:
                    messagebox.showerror("Error", msg)
                    return
                
                messagebox.showinfo("Success", msg)
                dialog.destroy()
            
            ttk.Button(container, text="Reset Password", command=do_reset).pack(pady=10)
            otp_entry.bind('<Return>', lambda e: do_reset())
            
            def resend_otp():
                otp, error = self.profile_manager.request_password_reset(email)
                if error:
                    messagebox.showerror("Error", error)
                    return
                messagebox.showinfo(
                    "OTP Sent",
                    f"A new OTP has been sent to {email}.\n\n(Demo mode - your OTP is: {otp})"
                )
            
            resend_link = ttk.Label(container, text="Resend OTP", foreground="blue", cursor="hand2")
            resend_link.pack(pady=(0, 5))
            resend_link.bind('<Button-1>', lambda e: resend_otp())
        
        build_step_email()


    def show_client_login(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Client Login / Register")
        dialog.geometry("400x450")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Client Login / Register", style='Title.TLabel').pack(pady=10)
        
        notebook = ttk.Notebook(dialog)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Login tab
        login_frame = ttk.Frame(notebook)
        notebook.add(login_frame, text="Login")
        
        ttk.Label(login_frame, text="Enter your registered Email:").pack(pady=10)
        login_email = ttk.Entry(login_frame, width=35)
        login_email.pack(pady=5)
        
        ttk.Label(login_frame, text="Password:").pack(pady=5)
        login_password = ttk.Entry(login_frame, width=35, show='*')
        login_password.pack(pady=5)
        self._add_show_password_toggle_pack(login_frame, login_password)
        
        def do_login():
            email = login_email.get().strip()
            password = login_password.get().strip()
            
            if not email or not password:
                messagebox.showerror("Error", "Please enter both email and password.")
                return
            
            profile, error = self.profile_manager.login(email, password)
            if error:
                messagebox.showerror("Error", error)
                return
            
            self.current_user = 'client'
            self.current_client_id = profile['id']
            dialog.destroy()
            self.show_client_dashboard(profile)
        
        ttk.Button(login_frame, text="Login", command=do_login).pack(pady=20)
        login_email.bind('<Return>', lambda e: do_login())
        login_password.bind('<Return>', lambda e: do_login())
        
        forgot_link = ttk.Label(login_frame, text="Forgot password?", foreground="blue", cursor="hand2")
        forgot_link.pack(pady=(0, 10))
        forgot_link.bind('<Button-1>', lambda e: self.show_forgot_password_dialog())
        
        # Register tab
        register_frame = ttk.Frame(notebook)
        notebook.add(register_frame, text="Register")
        
        reg_fields = {}
        fields = [
            ('name', "Full Name"),
            ('email', "Email"),
            ('phone', "Phone Number (9-10 digits)"),
            ('password', "Password"),
            ('confirm_password', "Confirm Password"),
            ('company', "Company (optional)"),
            ('industry', "Industry (optional)")
        ]
        
        field_max_lengths = {
            'name': MAX_NAME_LENGTH,
            'company': MAX_COMPANY_LENGTH,
            'industry': MAX_INDUSTRY_LENGTH,
        }
        
        for i, (key, label) in enumerate(fields):
            ttk.Label(register_frame, text=label).grid(row=i, column=0, sticky='w', padx=5, pady=3)
            show_char = '*' if key in ('password', 'confirm_password') else None
            entry = ttk.Entry(register_frame, width=30, show=show_char) if show_char else ttk.Entry(register_frame, width=30)
            entry.grid(row=i, column=1, padx=5, pady=3)
            if key in ('password', 'confirm_password'):
                self._add_show_password_toggle(register_frame, entry, row=i, column=2)
            if key in field_max_lengths:
                self._limit_entry_length(entry, field_max_lengths[key])
            reg_fields[key] = entry
        
        def do_register():
            name = reg_fields['name'].get().strip()
            email = reg_fields['email'].get().strip()
            phone = reg_fields['phone'].get().strip()
            password = reg_fields['password'].get().strip()
            confirm_password = reg_fields['confirm_password'].get().strip()
            company = reg_fields['company'].get().strip()
            industry = reg_fields['industry'].get().strip()
            
            if not name:
                messagebox.showerror("Error", "Name is required.")
                return
            if not email or not is_valid_email(email):
                messagebox.showerror("Error", "Please enter a valid email address.")
                return
            if not phone or not is_valid_phone(phone):
                messagebox.showerror("Error", "Phone number must be 9 to 10 digits (numbers only).")
                return
            if not is_valid_password(password):
                messagebox.showerror("Error", PASSWORD_REQUIREMENTS_MSG)
                return
            if password != confirm_password:
                messagebox.showerror("Error", "Passwords do not match.")
                return
            
            profile, error = self.profile_manager.add_profile(name, email, phone, password, company, industry)
            if error:
                messagebox.showerror("Error", error)
                return
            
            messagebox.showinfo("Success", f"Profile created successfully! Your Client ID is {profile['id']}.")
            self.current_user = 'client'
            self.current_client_id = profile['id']
            dialog.destroy()
            self.show_client_dashboard(profile)
        
        ttk.Button(register_frame, text="Register", command=do_register).grid(row=len(fields), column=0, columnspan=2, pady=20)


    def show_client_dashboard(self, profile):
        self.clear_frame()
        
        # Header
        ttk.Label(self.root, text=f"Client Dashboard - {profile['name']}", style='Title.TLabel').pack(pady=10)
        
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Left panel
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side='left', fill='y', padx=(0, 10))
        
        ttk.Button(button_frame, text="View My Profile", 
                  command=lambda: self.show_client_profile(profile['id']), width=25).pack(pady=5)
        ttk.Button(button_frame, text="Update My Profile", 
                  command=lambda: self.show_client_update_profile(profile['id']), width=25).pack(pady=5)
        ttk.Button(button_frame, text="Add Appointment", 
                  command=lambda: self.show_client_add_appointment(profile['id']), width=25).pack(pady=5)
        ttk.Button(button_frame, text="View My Appointments", 
                  command=lambda: self.show_client_view_appointments(profile['id']), width=25).pack(pady=5)
        ttk.Button(button_frame, text="Update My Appointment", 
                  command=lambda: self.show_client_update_appointment(profile['id']), width=25).pack(pady=5)
        ttk.Button(button_frame, text="Logout", 
                  command=self.client_logout, width=25).pack(pady=5)
        
        # Right panel
        self.client_content_frame = ttk.Frame(main_frame)
        self.client_content_frame.pack(side='right', fill='both', expand=True)
        
        ttk.Label(self.client_content_frame, text="Select an option from the left panel.", 
                  style='Heading.TLabel').pack(pady=50)


    def client_logout(self):
        self.current_user = None
        self.current_client_id = None
        self.show_main_menu()


    def clear_client_content(self):
        for widget in self.client_content_frame.winfo_children():
            widget.destroy()


    def show_client_profile(self, client_id):
        self.clear_client_content()
        
        profile = self.profile_manager.get_profile(client_id)
        if not profile:
            ttk.Label(self.client_content_frame, text="Profile not found.").pack(pady=20)
            return
        
        frame = ttk.Frame(self.client_content_frame)
        frame.pack(pady=20, padx=20, fill='x')
        
        fields = ['id', 'name', 'email', 'phone', 'company', 'industry', 'notes']
        for field in fields:
            ttk.Label(frame, text=f"{field.capitalize()}:", font=('Helvetica', 10, 'bold')).grid(
                row=fields.index(field), column=0, sticky='w', pady=3, padx=(0, 10))
            ttk.Label(frame, text=str(profile.get(field, ''))).grid(
                row=fields.index(field), column=1, sticky='w', pady=3)


    def show_client_update_profile(self, client_id):
        self.clear_client_content()
        
        profile = self.profile_manager.get_profile(client_id)
        if not profile:
            ttk.Label(self.client_content_frame, text="Profile not found.").pack(pady=20)
            return
        
        ttk.Label(self.client_content_frame, text="Update My Profile", style='Heading.TLabel').pack(pady=10)
        ttk.Label(self.client_content_frame,
                  text="Leave blank to keep the current value. For optional fields, tick 'Clear' to erase it.").pack()
        
        frame = ttk.Frame(self.client_content_frame)
        frame.pack(pady=20, padx=20)
        
        field_max_lengths = {
            'name': MAX_NAME_LENGTH,
            'company': MAX_COMPANY_LENGTH,
            'industry': MAX_INDUSTRY_LENGTH,
            'notes': MAX_NOTES_LENGTH,
        }
        
        # Only these are genuinely optional and allowed to be blank in
        # storage - name/email/phone are required and can't be cleared.
        clearable_fields = {'company', 'industry', 'notes'}
        
        entries = {}
        clear_vars = {}
        fields = ['name', 'email', 'phone', 'company', 'industry', 'notes']
        for i, field in enumerate(fields):
            ttk.Label(frame, text=f"{field.capitalize()}:").grid(row=i, column=0, sticky='w', pady=3, padx=5)
            entry = ttk.Entry(frame, width=35)
            entry.insert(0, str(profile.get(field, '')))
            entry.grid(row=i, column=1, pady=3, padx=5)
            if field in field_max_lengths:
                self._limit_entry_length(entry, field_max_lengths[field])
            entries[field] = entry
            
            if field in clearable_fields:
                clear_var = tk.BooleanVar(value=False)
                
                def make_toggle(entry=entry, clear_var=clear_var):
                    def toggle():
                        entry.configure(state='disabled' if clear_var.get() else 'normal')
                    return toggle
                
                check = ttk.Checkbutton(frame, text="Clear", variable=clear_var, command=make_toggle())
                check.grid(row=i, column=2, sticky='w', padx=(5, 0))
                clear_vars[field] = clear_var
        
        def do_update():
            updates = {}
            for field, entry in entries.items():
                if field in clear_vars and clear_vars[field].get():
                    updates[field] = ""
                    continue
                
                value = entry.get().strip()
                if value:
                    # Validate email and phone
                    if field == 'email' and not is_valid_email(value):
                        messagebox.showerror("Error", "Invalid email format.")
                        return
                    if field == 'phone' and not is_valid_phone(value):
                        messagebox.showerror("Error", "Phone number must be 9 to 10 digits.")
                        return
                    updates[field] = value
            
            if not updates:
                messagebox.showinfo("Info", "No changes made.")
                return
            
            success, msg = self.profile_manager.update_profile(client_id, updates)
            if not success:
                messagebox.showerror("Error", msg)
                return
            
            messagebox.showinfo("Success", "Your profile has been updated successfully.")
            self.show_client_profile(client_id)
        
        ttk.Button(self.client_content_frame, text="Update Profile", command=do_update).pack(pady=10)
        
        # ---------------------------------------------------------
        # Change Password section
        # ---------------------------------------------------------
        ttk.Separator(self.client_content_frame, orient='horizontal').pack(fill='x', pady=15, padx=20)
        ttk.Label(self.client_content_frame, text="Change Password", style='Heading.TLabel').pack(pady=5)
        
        pw_frame = ttk.Frame(self.client_content_frame)
        pw_frame.pack(pady=10, padx=20)
        
        ttk.Label(pw_frame, text="Current Password:").grid(row=0, column=0, sticky='w', pady=3, padx=5)
        current_pw_entry = ttk.Entry(pw_frame, width=30, show='*')
        current_pw_entry.grid(row=0, column=1, pady=3, padx=5)
        self._add_show_password_toggle(pw_frame, current_pw_entry, row=0, column=2)
        
        ttk.Label(pw_frame, text="New Password:").grid(row=1, column=0, sticky='w', pady=3, padx=5)
        new_pw_entry = ttk.Entry(pw_frame, width=30, show='*')
        new_pw_entry.grid(row=1, column=1, pady=3, padx=5)
        self._add_show_password_toggle(pw_frame, new_pw_entry, row=1, column=2)
        
        ttk.Label(pw_frame, text="Confirm New Password:").grid(row=2, column=0, sticky='w', pady=3, padx=5)
        confirm_pw_entry = ttk.Entry(pw_frame, width=30, show='*')
        confirm_pw_entry.grid(row=2, column=1, pady=3, padx=5)
        self._add_show_password_toggle(pw_frame, confirm_pw_entry, row=2, column=2)
        
        def do_change_password():
            current_password = current_pw_entry.get().strip()
            new_password = new_pw_entry.get().strip()
            confirm_password = confirm_pw_entry.get().strip()
            
            if not current_password or not new_password or not confirm_password:
                messagebox.showerror("Error", "Please fill in all password fields.")
                return
            
            # Verify the current password is correct before allowing a change
            _, error = self.profile_manager.login(profile['email'], current_password)
            if error:
                messagebox.showerror("Error", "Current password is incorrect.")
                return
            
            if new_password != confirm_password:
                messagebox.showerror("Error", "New passwords do not match.")
                return
            
            success, msg = self.profile_manager.change_password(client_id, new_password)
            if not success:
                messagebox.showerror("Error", msg)
                return
            
            messagebox.showinfo("Success", msg)
            current_pw_entry.delete(0, tk.END)
            new_pw_entry.delete(0, tk.END)
            confirm_pw_entry.delete(0, tk.END)
        
        ttk.Button(self.client_content_frame, text="Change Password", command=do_change_password).pack(pady=10)


    def show_client_add_appointment(self, client_id):
        self.clear_client_content()
        
        profile = self.profile_manager.get_profile(client_id)
        if not profile:
            ttk.Label(self.client_content_frame, text="Profile not found.").pack(pady=20)
            return
        
        ttk.Label(self.client_content_frame, text=f"Add Appointment for {profile['name']}", 
                  style='Heading.TLabel').pack(pady=10)

        barred_until = self.appointment_manager.get_barred_until(client_id)
        if barred_until:
            ttk.Label(
                self.client_content_frame,
                text=("BOOKING BARRED: You missed an appointment and cannot book or enter "
                      f"until {barred_until.strftime('%Y-%m-%d %H:%M')}."),
                foreground="red", wraplength=500
            ).pack(pady=10)
            return
        
        frame = ttk.Frame(self.client_content_frame)
        frame.pack(pady=20, padx=20)
        
        ttk.Label(frame, text="Date:").grid(row=0, column=0, sticky='w', pady=3, padx=5)
        date_frame, get_date_str = self._build_date_picker(frame)
        date_frame.grid(row=0, column=1, sticky='w', pady=3, padx=5)
        
        ttk.Label(frame, text="Time:").grid(row=1, column=0, sticky='w', pady=3, padx=5)
        time_frame, get_time_str = self._build_time_picker(frame)
        time_frame.grid(row=1, column=1, sticky='w', pady=3, padx=5)
        
        ttk.Label(frame, text="Purpose/Notes:").grid(row=2, column=0, sticky='w', pady=3, padx=5)
        purpose_entry = ttk.Entry(frame, width=35)
        purpose_entry.grid(row=2, column=1, pady=3, padx=5)
        self._limit_entry_length(purpose_entry, MAX_PURPOSE_LENGTH)
        
        def do_add():
            date_str = get_date_str()
            time_str = get_time_str()
            purpose = purpose_entry.get().strip()
            
            if not purpose:
                messagebox.showerror("Error", "Purpose/Notes is required.")
                return
            
            appointment, error = self.appointment_manager.add_appointment(client_id, date_str, time_str, purpose)
            if error:
                messagebox.showerror("Error", error)
                return
            
            messagebox.showinfo("Success", f"Appointment #{appointment['id']} added successfully.")
            self.show_client_view_appointments(client_id)
        
        ttk.Button(self.client_content_frame, text="Add Appointment", command=do_add).pack(pady=10)


    def show_client_view_appointments(self, client_id):
        self.clear_client_content()
        
        appointments = self.appointment_manager.get_client_appointments(client_id)
        if not appointments:
            ttk.Label(self.client_content_frame, text="You have no appointments yet.").pack(pady=20)
            return
        
        columns = ('ID', 'Date', 'Time', 'Purpose', 'Status')
        tree = ttk.Treeview(self.client_content_frame, columns=columns, show='headings', height=12)
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=120)
        
        for app in sorted(appointments, key=lambda x: (x['date'], x['time'])):
            tree.insert('', 'end', values=(app['id'], app['date'], app['time'], app['purpose'], app['status']))
        
        scrollbar = ttk.Scrollbar(self.client_content_frame, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')


    def show_client_update_appointment(self, client_id):
        self.clear_client_content()
        
        appointments = self.appointment_manager.get_client_appointments(client_id)
        if not appointments:
            ttk.Label(self.client_content_frame, text="You have no appointments.").pack(pady=20)
            return

        # Only Scheduled appointments are editable. Completed, Missed,
        # Checked In, and Cancelled appointments remain visible in the normal
        # appointment-history page but cannot be selected or changed here.
        scheduled_apps = [
            app for app in appointments
            if app.get('status') == 'Scheduled'
        ]

        if not scheduled_apps:
            ttk.Label(
                self.client_content_frame,
                text="You have no Scheduled appointments available to update.\n"
                     "Completed, Missed, Checked In, and Cancelled appointments cannot be changed.",
                justify='center'
            ).pack(pady=20)
            return
        
        ttk.Label(self.client_content_frame, text="Scheduled Appointments", style='Heading.TLabel').pack(pady=10)
        
        sorted_apps = sorted(scheduled_apps, key=lambda x: (x['date'], x['time']))
        
        # Show appointments list
        columns = ('ID', 'Date', 'Time', 'Purpose', 'Status')
        tree = ttk.Treeview(self.client_content_frame, columns=columns, show='headings', height=6)
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        
        for app in sorted_apps:
            tree.insert('', 'end', values=(app['id'], app['date'], app['time'], app['purpose'], app['status']))
        
        tree.pack(pady=10)
        
        # Appointment selector - picking from a dropdown of real appointments
        # instead of typing an ID removes the chance of a typo/invalid ID.
        ttk.Label(self.client_content_frame, text="Select an appointment to update:", 
                  style='Heading.TLabel').pack(pady=5)
        
        options = [
            f"#{a['id']} - {a['date']} {a['time']} - {a['purpose']} ({a['status']})"
            for a in sorted_apps
        ]
        id_by_option = {opt: a['id'] for opt, a in zip(options, sorted_apps)}
        
        select_var = tk.StringVar()
        select_combo = ttk.Combobox(self.client_content_frame, textvariable=select_var,
                                     values=options, width=65, state='readonly')
        select_combo.pack(pady=5)
        
        form_container = ttk.Frame(self.client_content_frame)
        form_container.pack(pady=10, padx=20)
        
        # Holds references to the currently-built pickers/entries so
        # do_update() can read them after the form is rebuilt per selection.
        current_form = {}
        
        def clear_form():
            for w in form_container.winfo_children():
                w.destroy()
            current_form.clear()
        
        def build_form(app_id):
            clear_form()
            app = next((a for a in sorted_apps if a['id'] == app_id), None)
            if not app:
                return
            
            ttk.Label(form_container, text=f"Current: {app['date']} {app['time']} - {app['status']}",
                      foreground="gray").grid(row=0, column=0, columnspan=3, sticky='w', pady=(0, 10))
            
            # --- Date ---
            change_date_var = tk.BooleanVar(value=False)
            date_frame, get_date_str = self._build_date_picker(form_container, initial=app['date'])
            
            def toggle_date():
                new_state = 'readonly' if change_date_var.get() else 'disabled'
                for child in date_frame.winfo_children():
                    if isinstance(child, ttk.Combobox):
                        child.configure(state=new_state)
            
            ttk.Checkbutton(form_container, text="Change Date", variable=change_date_var,
                             command=toggle_date).grid(row=1, column=0, sticky='w', pady=3, padx=5)
            date_frame.grid(row=1, column=1, sticky='w', pady=3, padx=5)
            toggle_date()
            
            # --- Time ---
            change_time_var = tk.BooleanVar(value=False)
            time_frame, get_time_str = self._build_time_picker(form_container, initial=app['time'])
            
            def toggle_time():
                new_state = 'readonly' if change_time_var.get() else 'disabled'
                for child in time_frame.winfo_children():
                    if isinstance(child, ttk.Combobox):
                        child.configure(state=new_state)
            
            ttk.Checkbutton(form_container, text="Change Time", variable=change_time_var,
                             command=toggle_time).grid(row=2, column=0, sticky='w', pady=3, padx=5)
            time_frame.grid(row=2, column=1, sticky='w', pady=3, padx=5)
            toggle_time()
            
            # --- Purpose (plain text - leave blank to keep current) ---
            ttk.Label(form_container, text="Purpose (optional):").grid(row=3, column=0, sticky='w', pady=3, padx=5)
            purpose_entry = ttk.Entry(form_container, width=30)
            purpose_entry.grid(row=3, column=1, sticky='w', pady=3, padx=5)
            self._limit_entry_length(purpose_entry, MAX_PURPOSE_LENGTH)
            
            current_form['app_id'] = app_id
            current_form['change_date_var'] = change_date_var
            current_form['get_date_str'] = get_date_str
            current_form['change_time_var'] = change_time_var
            current_form['get_time_str'] = get_time_str
            current_form['purpose_entry'] = purpose_entry
        
        def on_select(event=None):
            selected = select_var.get()
            if selected in id_by_option:
                build_form(id_by_option[selected])
        
        select_combo.bind('<<ComboboxSelected>>', on_select)
        
        def do_update():
            if not current_form:
                messagebox.showerror("Error", "Please select an appointment to update.")
                return
            
            app_id = current_form['app_id']
            date_str = current_form['get_date_str']() if current_form['change_date_var'].get() else None
            time_str = current_form['get_time_str']() if current_form['change_time_var'].get() else None
            purpose = current_form['purpose_entry'].get().strip() or None
            
            if not date_str and not time_str and not purpose:
                messagebox.showinfo("Info", "No changes selected.")
                return
            
            success, msg = self.appointment_manager.update_appointment(app_id, client_id, date_str, time_str, purpose)
            if not success:
                messagebox.showerror("Error", msg)
                return
            
            messagebox.showinfo("Success", msg)
            self.show_client_update_appointment(client_id)
        
        ttk.Button(self.client_content_frame, text="Update Appointment", command=do_update).pack(pady=10)

