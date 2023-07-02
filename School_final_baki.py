import tkinter as tk
from tkinter import font
from tkcalendar import Calendar
from tkinter import filedialog
from sqlite3 import * 

class School:
    def __init__(self, window):
        self.window = window
        self.window.title("PALLPUBB")
        self.window.geometry("1920x1050")
        self.window.minsize(1920, 1050)
        self.window.configure(bg="#324370")


        def clear_text(event):
            search_bar.delete(0, tk.END)

        def open_calendar():
            def get_date():
                selected_date = cal.selection_get()
                joining_date.delete(0, tk.END)
                joining_date.insert(tk.END, selected_date.strftime("%d-%m-%Y"))
                top.destroy()

            top = tk.Toplevel(window)
            top.title("Select Joining Date")
            top.geometry("400x320")
            top.configure(bg="#324370")
            top.grab_set()

            cal = Calendar(top, selectmode="day")
            cal.pack(pady=20)

            select_button = tk.Button(top, text="Select", command=get_date, fg="white", bg="#698ED4",
                                      font=("Helvetica bold", 14, "bold"))
            select_button.pack(pady=10)

        def open_text_file():
            filepath = filedialog.askopenfilename(initialdir="/", title="Select Text File",
                                                  filetypes=(("Text Files", "*.txt"), ("All Files", "*.*")))

        def back():
            self.window.destroy()
            
        def clear():
            for entry in entry_list:
                entry.delete(0, tk.END)


        # Create the title bar and set the bg color of the title bar
        title_bar = tk.Frame(window, bg="#769ADD", height=200)
        title_bar.pack(fill=tk.X)

        # Create the title label in the title bar of PULLPUBB
        title_font = font.Font(family="Helvetica bold", size=60, weight="bold")
        title_label = tk.Label(title_bar, text="SCHOOL", fg="white", bg="#769ADD", font=title_font)
        title_label.pack(pady=10)

        # Create back button to go back to the main PULLPUBB dashboard
        button_font = font.Font(family="Helvetica bold", size=12, weight="bold")

        back_button = tk.Button(window, text="BACK", bg="#255ABC", fg="white", width=10, font=button_font, command=back)
        back_button.place(x=20, y=140)
        back_button.configure(activebackground="#255ABC", activeforeground="white")

        # Create a frame for the input fields and labels
        input_frame = tk.Frame(window, bg="#324370")
        input_frame.place(x=10, y=200)

        # Create a white line to separate the sections
        line = tk.Frame(input_frame, bg="white", width=2)
        line.grid(row=0, column=2, rowspan=11, sticky="ns", padx=10)

       # Create input fields and labels on the left side
        labels = [
            "School Name:", "Principal Name:", "Joining Date:", "School Email ID:", "School Address:"
        ]
        entry_list = []

        for i, label_text in enumerate(labels):
            label = tk.Label(input_frame, text=label_text, bg="#324370", fg="white",
                            font=("Helvetica bold", 20, "bold"))
            label.grid(row=i, column=0, sticky="w", pady=5, padx=5)

            if label_text == "Joining Date:":
                joining_date = tk.Entry(input_frame, bg="white", font=("Helvetica", 20), width=10)
                joining_date.grid(row=i, column=1, pady=5, padx=5, sticky="we")
                entry_list.append(joining_date)
                joining_date.bind("<Button-1>", lambda event: open_calendar())
            elif label_text == "School Address:":
                entry = tk.Text(input_frame, bg="white", font=("Helvetica", 20), width=10, height=2)
                entry.grid(row=i, column=1, pady=0, padx=5, sticky="we")
                entry_list.append(entry)
            else:
                entry = tk.Entry(input_frame, bg="white", font=("Helvetica", 20), width=10)
                entry.grid(row=i, column=1, pady=5, padx=5, sticky="we")
                entry_list.append(entry)

        # Create input fields and labels on the right side
        right_labels = [
            "Contact Person Name:", "Contact Person Email ID:",
            "Magazine Copy:", "Instagram ID:", "Facebook ID:"
        ]

        for i, label_text in enumerate(right_labels):
            label = tk.Label(input_frame, text=label_text, bg="#324370", fg="white",
                            font=("Helvetica bold", 20, "bold"))
            label.grid(row=i, column=3, sticky="w", pady=5, padx=5)

            if label_text == "Magazine Copy:":
                magazine_copy = tk.Button(input_frame, text="", font=("Helvetica bold", 16), width=10)
                magazine_copy.grid(row=i, column=4, pady=5, padx=5, sticky="we")
                # entry_list.append(magazine_copy)
            else:
                entry = tk.Entry(input_frame, bg="white", font=("Helvetica", 20), width=10)
                entry.grid(row=i, column=4, pady=5, padx=5, sticky="we")
                entry_list.append(entry)

        # Create a submit button
        submit_button = tk.Button(input_frame, text="SUBMIT", fg="white", bg="#698ED4",
                                font=("Helvetica bold", 20, "bold"), command=lambda: submit(entry_list[:10]))
        submit_button.grid(row=11, column=0, columnspan=5, pady=20)
        submit_button.configure(activebackground="#698ED4", activeforeground="#FFFFFF")

        # Create the sidebar on the right side
        sidebar = tk.Frame(window, bg="#698ED4", width=400)
        sidebar.pack(fill=tk.BOTH, side=tk.RIGHT)

        # Create the search bar and button in the sidebar
        search_text = tk.StringVar()
        search_text.set("School ID")

        search_bar = tk.Entry(sidebar, bg="white", font=("Helvetica bold", 20, "bold"), width=20,
                              textvariable=search_text)
        search_bar.grid(row=0, column=0, padx=10, pady=(50, 30))
        search_bar.bind("<Button-1>", clear_text)

        search_button = tk.Button(sidebar, bg="white", text="SEARCH", font=("Helvetica bold", 20, "bold"))
        search_button.grid(row=0, column=1, padx=10, pady=(50, 30))

        # Create a delete button
        delete_button = tk.Button(sidebar, bg="white", text="DELETE", font=("Helvetica bold", 20, "bold"), width=20)
        delete_button.grid(row=1, column=0, columnspan=2, padx=10, pady=30)

        # Create an edit button
        edit_button = tk.Button(sidebar, bg="white", text="EDIT", font=("Helvetica bold", 20, "bold"), width=20)
        edit_button.grid(row=2, column=0, columnspan=2, padx=10, pady=30)

        # Create a clear button
        clear_button = tk.Button(sidebar, bg="white", text="CLEAR ALL", font=("Helvetica bold", 20, "bold"), width=20, command=clear)
        clear_button.grid(row=3, column=0, columnspan=2, padx=10, pady=30)

# database  
def submit(entries):
    conn = connect('school.db')
    con_cursor = conn.cursor()
    query_table = 'CREATE TABLE IF NOT EXISTS schools (S_ID INTEGER PRIMARY KEY AUTOINCREMENT, S_NAME TEXT NOT NULL, S_ADDRESS TEXT NOT NULL, PRINCIPAL_NAME TEXT NOT NULL, JOINING_DATE VARCHAR NOT NULL, SCHOOL_EMAIL TEXT NOT NULL, CONTACT_PERSON_NAME TEXT NOT NULL, CONTACT_PERSON_EMAIL TEXT NOT NULL, INSTAGRAM_ID TEXT NOT NULL, FACEBOOK_ID TEXT NOT NULL)'
    con_cursor.execute(query_table)
    query_entries = 'INSERT INTO schools (S_NAME, S_ADDRESS, PRINCIPAL_NAME, JOINING_DATE, SCHOOL_EMAIL, CONTACT_PERSON_NAME, CONTACT_PERSON_EMAIL, INSTAGRAM_ID, FACEBOOK_ID) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)'
    values = [entry.get() for entry in entries]
    con_cursor.execute(query_entries, values)
    conn.commit()
    con_cursor.close()
    conn.close()


if __name__ == "__main__":
    window = tk.Tk()
    app = School(window)
    window.mainloop()