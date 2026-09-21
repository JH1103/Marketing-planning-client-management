"""Admin pages for the Marketing Planning App.

Do not run this file directly. Run main_menu.py.
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
from datetime import datetime

MAX_NAME_LENGTH = 50
MAX_UNBAR_REASON_LENGTH = 300
NO_SHOW_GRACE_MINUTES = 15
MIN_PASSWORD_LENGTH = 8
PASSWORD_REQUIREMENTS_MSG = (
    f"Password must be at least {MIN_PASSWORD_LENGTH} characters long "
    "and contain at least one letter and one number."
)

def is_valid_password(value):
    if len(value) < MIN_PASSWORD_LENGTH:
        return False
    return any(c.isalpha() for c in value) and any(c.isdigit() for c in value)


class AdminPageMixin:
    def _build_admin_creation_form(self, dialog, frame, success_message_fn):
        """Shared by show_first_admin_setup and show_admin_add_admin so the
        name/password/confirm fields + validation only need to live in one
        place. success_message_fn(admin) returns the text shown on success."""
        ttk.Label(frame, text="Admin Name:").grid(row=0, column=0, sticky='w', pady=5)
        name_entry = ttk.Entry(frame, width=30)
        name_entry.grid(row=0, column=1, pady=5)

        ttk.Label(frame, text="Password:").grid(row=1, column=0, sticky='w', pady=5)
        pass_entry = ttk.Entry(frame, width=30, show='*')
        pass_entry.grid(row=1, column=1, pady=5)
        self._add_show_password_toggle(frame, pass_entry, row=1, column=2)

        ttk.Label(frame, text="Confirm Password:").grid(row=2, column=0, sticky='w', pady=5)
        confirm_entry = ttk.Entry(frame, width=30, show='*')
        confirm_entry.grid(row=2, column=1, pady=5)
        self._add_show_password_toggle(frame, confirm_entry, row=2, column=2)

        def create_admin():
            name = name_entry.get().strip()
            password = pass_entry.get().strip()
            confirm = confirm_entry.get().strip()

            if not name:
                messagebox.showerror("Error", "Name cannot be empty.")
                return
            if len(name) > MAX_NAME_LENGTH:
                messagebox.showerror("Error", f"Name must be {MAX_NAME_LENGTH} characters or fewer.")
                return
            if self.admin_manager.find_by_name(name):
                messagebox.showerror("Error", "An admin with this name already exists.")
                return
            if not is_valid_password(password):
                messagebox.showerror("Error", PASSWORD_REQUIREMENTS_MSG)
                return
            if password != confirm:
                messagebox.showerror("Error", "Passwords do not match.")
                return

            admin, error = self.admin_manager.add_admin(name, password)
            if error:
                messagebox.showerror("Error", error)
                return

            messagebox.showinfo("Success", success_message_fn(admin))
            dialog.destroy()

        ttk.Button(dialog, text="Create Admin", command=create_admin).pack(pady=20)


    def ensure_first_admin(self):
        if not self.admin_manager.records:
            # Create first admin via dialog
            self.show_first_admin_setup()


    def show_first_admin_setup(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("First-Time Setup: Create Admin Account")
        dialog.geometry("400x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="First-Time Setup", style='Title.TLabel').pack(pady=10)
        ttk.Label(dialog, text="Create the first Admin account.").pack()
        
        frame = ttk.Frame(dialog)
        frame.pack(pady=20, padx=20, fill='x')
        
        self._build_admin_creation_form(
            dialog, frame,
            success_message_fn=lambda admin: (
                f"Admin account created. Admin ID: {admin['id']}\n"
                "Please remember your ID and password."
            )
        )


    def show_admin_login(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Admin Login")
        dialog.geometry("350x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Admin Login", style='Title.TLabel').pack(pady=10)
        
        frame = ttk.Frame(dialog)
        frame.pack(pady=20, padx=20, fill='x')
        
        ttk.Label(frame, text="Admin ID:").grid(row=0, column=0, sticky='w', pady=5)
        id_entry = ttk.Entry(frame, width=25)
        id_entry.grid(row=0, column=1, pady=5)
        
        ttk.Label(frame, text="Password:").grid(row=1, column=0, sticky='w', pady=5)
        pass_entry = ttk.Entry(frame, width=25, show='*')
        pass_entry.grid(row=1, column=1, pady=5)
        self._add_show_password_toggle(frame, pass_entry, row=1, column=2)
        
        def do_login():
            try:
                admin_id = int(id_entry.get().strip())
            except ValueError:
                messagebox.showerror("Error", "Invalid Admin ID.")
                return
            password = pass_entry.get().strip()
            
            admin, error = self.admin_manager.login(admin_id, password)
            if error:
                messagebox.showerror("Error", error)
                return
            
            self.current_user = 'admin'
            self.current_admin_id = admin_id
            dialog.destroy()
            self.show_admin_dashboard(admin)
        
        ttk.Button(dialog, text="Login", command=do_login).pack(pady=20)


    def show_admin_dashboard(self, admin):
        self.clear_frame()
        self.root.geometry("1200x700")

        ttk.Label(self.root, text=f"Admin Dashboard - {admin['name']}", style='Title.TLabel').pack(pady=10)

        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side='left', fill='y', padx=(0, 10))

        ttk.Button(button_frame, text="View All Client Profiles", command=self.show_admin_view_profiles, width=25).pack(pady=5)
        ttk.Button(button_frame, text="View All Appointments", command=self.show_admin_view_appointments, width=25).pack(pady=5)
        ttk.Button(button_frame, text="Search Client Profiles", command=self.show_admin_search_profiles, width=25).pack(pady=5)
        ttk.Button(button_frame, text="Search Appointments by Client", command=self.show_admin_search_appointments, width=25).pack(pady=5)
        ttk.Button(button_frame, text="Check In / Update Status", command=self.show_admin_update_status, width=25).pack(pady=5)
        ttk.Button(button_frame, text="Audit / History", command=self.show_admin_audit_history, width=25).pack(pady=5)
        ttk.Button(button_frame, text="UNBAR CLIENT", command=self.show_admin_unbar_client, width=25).pack(pady=5)
        ttk.Button(button_frame, text="Add New Admin", command=self.show_admin_add_admin, width=25).pack(pady=5)
        ttk.Button(button_frame, text="Logout", command=self.admin_logout, width=25).pack(pady=5)

        self.content_frame = ttk.Frame(main_frame)
        self.content_frame.pack(side='right', fill='both', expand=True)

        ttk.Label(self.content_frame, text="Appointment Statistics", style='Heading.TLabel').pack(pady=(15, 10))
        stats = self.appointment_manager.get_statistics()
        stats_frame = ttk.Frame(self.content_frame)
        stats_frame.pack(fill='x', padx=10, pady=10)
        labels = ["Scheduled", "Checked In", "Completed", "Missed", "Cancelled", "Barred Clients"]
        for index, label in enumerate(labels):
            card = ttk.LabelFrame(stats_frame, text=label, padding=10)
            card.grid(row=index // 3, column=index % 3, padx=8, pady=8, sticky='nsew')
            ttk.Label(card, text=str(stats.get(label, 0)), font=('Helvetica', 18, 'bold')).pack()
        for col in range(3):
            stats_frame.columnconfigure(col, weight=1)

        ttk.Label(self.content_frame, text="Select an option from the left panel.").pack(pady=20)

    def show_admin_audit_history(self):
        """Display admin actions such as check-in, cancellation, completion and unbar."""
        self.clear_content_frame()
        ttk.Label(self.content_frame, text="Admin Audit / History", style='Heading.TLabel').pack(pady=10)

        history = self.appointment_manager.get_audit_history()
        if not history:
            ttk.Label(self.content_frame, text="No admin actions have been recorded yet.").pack(pady=20)
            return

        frame = ttk.Frame(self.content_frame)
        frame.pack(fill='both', expand=True, padx=5, pady=5)
        columns = ('Time', 'Admin', 'Action', 'Appointment', 'Client', 'Reason')
        tree = ttk.Treeview(frame, columns=columns, show='headings', height=18)
        widths = {'Time': 145, 'Admin': 150, 'Action': 110, 'Appointment': 90, 'Client': 160, 'Reason': 330}
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=widths[col], anchor='w')

        for item in history:
            admin = self.admin_manager.get_admin(item.get('admin_id'))
            admin_name = f"{admin['name']} (ID {admin['id']})" if admin else f"Admin ID {item.get('admin_id')}"
            profile = self.profile_manager.get_profile(item.get('client_id'))
            client_name = f"{profile['name']} (ID {profile['id']})" if profile else f"Client ID {item.get('client_id')}"
            tree.insert('', 'end', values=(
                item.get('timestamp', '-'), admin_name, item.get('action', '-'),
                item.get('appointment_id') or '-', client_name, item.get('reason') or '-'
            ))

        yscroll = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
        xscroll = ttk.Scrollbar(frame, orient='horizontal', command=tree.xview)
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        tree.grid(row=0, column=0, sticky='nsew')
        yscroll.grid(row=0, column=1, sticky='ns')
        xscroll.grid(row=1, column=0, sticky='ew')
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

    def show_admin_unbar_client(self):
        """Allow an admin to remove an active three-day bar with a reason."""
        self.clear_content_frame()

        ttk.Label(self.content_frame, text="Unbar Client", style='Heading.TLabel').pack(pady=10)
        ttk.Label(
            self.content_frame,
            text=("Use this only when the client has a reasonable explanation. "
                  "The reason and admin ID will be stored in the appointment history."),
            wraplength=480, justify='left'
        ).pack(pady=(0, 10))

        barred_clients = []
        for profile in self.profile_manager.get_all_profiles():
            barred_until = self.appointment_manager.get_barred_until(profile['id'])
            if barred_until:
                barred_clients.append((profile, barred_until))

        if barred_clients:
            tree_frame = ttk.Frame(self.content_frame)
            tree_frame.pack(fill='both', expand=True, padx=5, pady=5)
            columns = ('Client ID', 'Client Name', 'Email', 'Barred Until')
            tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=7)
            for col in columns:
                tree.heading(col, text=col)
                tree.column(col, width=120)
            for profile, barred_until in barred_clients:
                tree.insert('', 'end', values=(
                    profile['id'], profile['name'], profile['email'],
                    barred_until.strftime('%Y-%m-%d %H:%M')
                ))
            scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            tree.pack(side='left', fill='both', expand=True)
            scrollbar.pack(side='right', fill='y')
        else:
            ttk.Label(self.content_frame, text="There are currently no barred clients.").pack(pady=10)

        form = ttk.Frame(self.content_frame)
        form.pack(fill='x', padx=10, pady=10)
        ttk.Label(form, text="Client ID:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        client_id_entry = ttk.Entry(form, width=15)
        client_id_entry.grid(row=0, column=1, sticky='w', padx=5, pady=5)

        ttk.Label(form, text="Reason to unbar:").grid(row=1, column=0, sticky='nw', padx=5, pady=5)
        reason_text = scrolledtext.ScrolledText(form, width=45, height=5, wrap=tk.WORD)
        reason_text.grid(row=1, column=1, padx=5, pady=5)

        def do_unbar():
            try:
                client_id = int(client_id_entry.get().strip())
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid Client ID.")
                return

            profile = self.profile_manager.get_profile(client_id)
            if not profile:
                messagebox.showerror("Error", f"Client ID {client_id} was not found.")
                return

            reason = reason_text.get('1.0', 'end').strip()
            if not reason:
                messagebox.showerror("Reason Required", "Please write the reason for unbarring this client.")
                return
            if len(reason) > MAX_UNBAR_REASON_LENGTH:
                messagebox.showerror(
                    "Reason Too Long",
                    f"Reason must be {MAX_UNBAR_REASON_LENGTH} characters or fewer."
                )
                return

            if not messagebox.askyesno(
                "Confirm Unbar",
                f"Unbar {profile['name']} (Client ID {client_id})?\n\nReason: {reason}"
            ):
                return

            success, msg = self.appointment_manager.unbar_client(
                client_id, reason, self.current_admin_id
            )
            if not success:
                messagebox.showerror("Unable to Unbar", msg)
                return

            messagebox.showinfo("Client Unbarred", msg)
            self.show_admin_unbar_client()

        ttk.Button(form, text="Unbar Client", command=do_unbar).grid(
            row=2, column=1, sticky='w', padx=5, pady=10
        )


    def show_admin_add_admin(self):
        """Let a logged-in admin create another admin account."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add New Admin")
        dialog.geometry("400x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Add New Admin", style='Title.TLabel').pack(pady=10)
        
        frame = ttk.Frame(dialog)
        frame.pack(pady=20, padx=20, fill='x')
        
        self._build_admin_creation_form(
            dialog, frame,
            success_message_fn=lambda admin: (
                f"Admin account created. Admin ID: {admin['id']}\n"
                "Share this ID and password with the new admin."
            )
        )


    def admin_logout(self):
        self.current_user = None
        self.current_admin_id = None
        self.show_main_menu()


    def show_admin_view_profiles(self):
        self.clear_content_frame()
        
        profiles = self.profile_manager.get_all_profiles()
        if not profiles:
            ttk.Label(self.content_frame, text="No client profiles found.").pack(pady=20)
            return
        
        # Create Treeview. Account restriction information belongs on the
        # client profile page rather than on each individual appointment row.
        columns = ('ID', 'Name', 'Email', 'Phone', 'Company', 'Industry', 'Account Status', 'Barred Until')
        tree = ttk.Treeview(self.content_frame, columns=columns, show='headings', height=15)

        widths = {
            'ID': 55, 'Name': 120, 'Email': 180, 'Phone': 100,
            'Company': 120, 'Industry': 110, 'Account Status': 105,
            'Barred Until': 135
        }
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=widths[col], anchor='w')

        for p in profiles:
            barred_until = self.appointment_manager.get_barred_until(p['id'])
            account_status = 'Barred' if barred_until else 'Active'
            barred_text = barred_until.strftime('%Y-%m-%d %H:%M') if barred_until else '-'
            tree.insert('', 'end', values=(
                p['id'], p['name'], p['email'], p['phone'],
                p['company'] or '-', p['industry'] or '-',
                account_status, barred_text
            ))
        
        scrollbar = ttk.Scrollbar(self.content_frame, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')


    def show_admin_view_appointments(self):
        self.clear_content_frame()
        
        appointments = self.appointment_manager.get_all_appointments()
        if not appointments:
            ttk.Label(self.content_frame, text="No appointments found.").pack(pady=20)
            return
        
        columns = ('ID', 'Client', 'Date', 'Time', 'Purpose', 'Status')
        tree = ttk.Treeview(self.content_frame, columns=columns, show='headings', height=15)

        widths = {'ID': 55, 'Client': 180, 'Date': 95, 'Time': 70, 'Purpose': 240, 'Status': 100}
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=widths[col], anchor='w')

        for app in appointments:
            display = self.appointment_manager.get_appointment_display(app, self.profile_manager)
            tree.insert('', 'end', values=(display['id'], display['client'], display['date'],
                                          display['time'], display['purpose'], display['status']))
        
        scrollbar = ttk.Scrollbar(self.content_frame, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')


    def show_admin_search_profiles(self):
        self.clear_content_frame()
        
        frame = ttk.Frame(self.content_frame)
        frame.pack(fill='x', pady=10)
        
        ttk.Label(frame, text="Search by name, email, or company:").pack(side='left', padx=5)
        search_entry = ttk.Entry(frame, width=30)
        search_entry.pack(side='left', padx=5)
        
        result_frame = ttk.Frame(self.content_frame)
        result_frame.pack(fill='both', expand=True)
        
        def do_search():
            for widget in result_frame.winfo_children():
                widget.destroy()
            
            keyword = search_entry.get().strip()
            results = self.profile_manager.search_profiles(keyword)
            
            if not results:
                ttk.Label(result_frame, text="No matching client profiles found.").pack(pady=20)
                return
            
            columns = ('ID', 'Name', 'Email', 'Phone', 'Company', 'Industry', 'Account Status', 'Barred Until')
            tree = ttk.Treeview(result_frame, columns=columns, show='headings', height=12)
            
            for col in columns:
                tree.heading(col, text=col)
                tree.column(col, width=110)
            
            for p in results:
                barred_until = self.appointment_manager.get_barred_until(p['id'])
                account_status = 'Barred' if barred_until else 'Active'
                barred_until_text = barred_until.strftime('%Y-%m-%d %H:%M') if barred_until else '-'
                tree.insert('', 'end', values=(
                    p['id'], p['name'], p['email'], p['phone'],
                    p['company'] or '-', p['industry'] or '-',
                    account_status, barred_until_text
                ))
            
            scrollbar = ttk.Scrollbar(result_frame, orient='vertical', command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            
            tree.pack(side='left', fill='both', expand=True)
            scrollbar.pack(side='right', fill='y')
        
        ttk.Button(frame, text="Search", command=do_search).pack(side='left', padx=5)
        search_entry.bind('<Return>', lambda e: do_search())


    def show_admin_search_appointments(self):
        self.clear_content_frame()
        
        frame = ttk.Frame(self.content_frame)
        frame.pack(fill='x', pady=10)
        
        ttk.Label(frame, text="Enter client name to search:").pack(side='left', padx=5)
        search_entry = ttk.Entry(frame, width=30)
        search_entry.pack(side='left', padx=5)
        
        result_frame = ttk.Frame(self.content_frame)
        result_frame.pack(fill='both', expand=True)
        
        def do_search():
            for widget in result_frame.winfo_children():
                widget.destroy()
            
            keyword = search_entry.get().strip()
            results = self.appointment_manager.search_appointments_by_client(keyword, self.profile_manager)
            
            if not results:
                ttk.Label(result_frame, text="No matching appointments found.").pack(pady=20)
                return
            
            columns = ('ID', 'Client', 'Date', 'Time', 'Purpose', 'Status', 'Barred Until')
            tree = ttk.Treeview(result_frame, columns=columns, show='headings', height=12)
            
            for col in columns:
                tree.heading(col, text=col)
                tree.column(col, width=100)
            
            for app in results:
                display = self.appointment_manager.get_appointment_display(app, self.profile_manager)
                tree.insert('', 'end', values=(display['id'], display['client'], display['date'], 
                                              display['time'], display['purpose'], display['status'], display['barred_until']))
            
            scrollbar = ttk.Scrollbar(result_frame, orient='vertical', command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            
            tree.pack(side='left', fill='both', expand=True)
            scrollbar.pack(side='right', fill='y')
        
        ttk.Button(frame, text="Search", command=do_search).pack(side='left', padx=5)
        search_entry.bind('<Return>', lambda e: do_search())


    def show_admin_update_status(self):
        """Select an appointment row, then check in or apply a valid status change."""
        self.clear_content_frame()
        ttk.Label(self.content_frame, text="Select Appointment", style='Heading.TLabel').pack(pady=10)

        appointments = self.appointment_manager.get_all_appointments()
        if not appointments:
            ttk.Label(self.content_frame, text="No appointments found.").pack(pady=20)
            return

        tree_frame = ttk.Frame(self.content_frame)
        tree_frame.pack(fill='both', expand=True, pady=5)
        columns = ('ID', 'Client', 'Date', 'Time', 'Purpose', 'Appointment Status')
        tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=10, selectmode='browse')
        widths = {'ID': 55, 'Client': 190, 'Date': 95, 'Time': 70, 'Purpose': 260, 'Appointment Status': 150}
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=widths[col], anchor='w')

        item_to_app = {}
        for app in appointments:
            display = self.appointment_manager.get_appointment_display(app, self.profile_manager)
            item = tree.insert('', 'end', values=(display['id'], display['client'], display['date'],
                               display['time'], display['purpose'], display['status']))
            item_to_app[item] = app

        yscroll = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
        xscroll = ttk.Scrollbar(tree_frame, orient='horizontal', command=tree.xview)
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        tree.grid(row=0, column=0, sticky='nsew')
        yscroll.grid(row=0, column=1, sticky='ns')
        xscroll.grid(row=1, column=0, sticky='ew')
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        control = ttk.LabelFrame(self.content_frame, text="Selected Appointment", padding=10)
        control.pack(fill='x', padx=5, pady=10)
        selected_id = tk.StringVar(value="None")
        selected_status = tk.StringVar(value="-")
        status_var = tk.StringVar()

        ttk.Label(control, text="Appointment ID:").grid(row=0, column=0, sticky='w', padx=5, pady=3)
        ttk.Label(control, textvariable=selected_id, font=('Helvetica', 10, 'bold')).grid(row=0, column=1, sticky='w', padx=5, pady=3)
        ttk.Label(control, text="Current Status:").grid(row=0, column=2, sticky='w', padx=15, pady=3)
        ttk.Label(control, textvariable=selected_status, font=('Helvetica', 10, 'bold')).grid(row=0, column=3, sticky='w', padx=5, pady=3)

        ttk.Label(control, text="New Status:").grid(row=1, column=0, sticky='w', padx=5, pady=3)
        status_combo = ttk.Combobox(control, textvariable=status_var, width=18, state='readonly', values=())
        status_combo.grid(row=1, column=1, sticky='w', padx=5, pady=3)
        hint = ttk.Label(control, text="Click an appointment row above.", foreground='gray')
        hint.grid(row=2, column=0, columnspan=4, sticky='w', padx=5, pady=4)

        selected_app = {'record': None}

        def on_select(event=None):
            selection = tree.selection()
            if not selection:
                return
            app = item_to_app.get(selection[0])
            if not app:
                return
            selected_app['record'] = app
            selected_id.set(str(app['id']))
            selected_status.set(app.get('status', '-'))
            allowed = self.appointment_manager.get_allowed_admin_statuses(app)
            status_combo['values'] = allowed
            status_var.set('')
            if app.get('status') == 'Scheduled':
                hint.configure(text="Use Check In Client when the appointment time is reached, or select Cancelled.")
            elif app.get('status') == 'Checked In':
                hint.configure(text="Select Completed after the appointment/service is finished.")
            else:
                hint.configure(text=f"{app.get('status')} is final and cannot be changed.")

        tree.bind('<<TreeviewSelect>>', on_select)

        def do_check_in():
            app = selected_app['record']
            if not app:
                messagebox.showerror("Error", "Please click an appointment row first.")
                return
            success, msg = self.appointment_manager.check_in_client(app['id'], self.current_admin_id)
            if success:
                messagebox.showinfo("Check In", msg)
                self.show_admin_update_status()
            else:
                messagebox.showerror("Entry Denied", msg)

        def do_update_status():
            app = selected_app['record']
            if not app:
                messagebox.showerror("Error", "Please click an appointment row first.")
                return
            new_status = status_var.get().strip()
            if not new_status:
                messagebox.showerror("Error", "Please select an available new status.")
                return

            reason = ""
            if new_status == 'Cancelled':
                reason = simpledialog.askstring(
                    "Cancellation Reason",
                    "Please enter the reason for cancelling this appointment:",
                    parent=self.root
                )
                if reason is None:
                    return
                reason = reason.strip()
                if not reason:
                    messagebox.showerror("Reason Required", "A cancellation reason is required.")
                    return

            if not messagebox.askyesno(
                "Confirm",
                f"Change Appointment #{app['id']} from '{app['status']}' to '{new_status}'?"
            ):
                return

            success, msg = self.appointment_manager.update_appointment_status_admin(
                app['id'], new_status, self.current_admin_id, reason
            )
            if success:
                messagebox.showinfo("Success", msg)
                self.show_admin_update_status()
            else:
                messagebox.showerror("Error", msg)

        buttons = ttk.Frame(control)
        buttons.grid(row=3, column=0, columnspan=4, sticky='w', pady=8)
        ttk.Button(buttons, text="Check In Client", command=do_check_in).pack(side='left', padx=5)
        ttk.Button(buttons, text="Update Status", command=do_update_status).pack(side='left', padx=5)
        ttk.Button(buttons, text="Refresh List", command=self.show_admin_update_status).pack(side='left', padx=5)

    def clear_content_frame(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

