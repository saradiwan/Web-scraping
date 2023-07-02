import tkinter as tk
from tkinter import font
from School_final_baki import School
from student_modified import Student
#from database1 import submit
from sqlite3 import *
class IMS:
    def __init__(self, window):
        self.window = window
        self.window.title("PALLPUBB")
        self.window.geometry("1920x1050")
        self.window.configure(bg="#324370")

        def back():
            self.window.destroy()
        
        # Create the title bar and set the bg color of the title bar    
        title_bar = tk.Frame(window, bg="#769ADD", height=200)
        title_bar.pack(fill=tk.X)

        # Create the title label in the title bar of PULLPUBB
        title_font = font.Font(family="Helvetica bold", size=60, weight="bold")
        title_label = tk.Label(title_bar, text="PALLPUBB", fg="white", bg="#769ADD", font=title_font)
        title_label.pack(pady=10)

        # Create back button to go back to the main PULLPUBB dashboard
        button_font = font.Font(family="Helvetica bold", size=20, weight="bold")

        back_button = tk.Button(window, text="BACK", bg="#255ABC", fg="white", width=10, font=button_font, command=back)
        back_button.place(x=10, y=150)
        back_button.configure(activebackground="#255ABC", activeforeground="white")

        # Create the rectangular box for The School Diaries
        school_diaries_rectangle = tk.Frame(window, bg="#2F4D99", padx=50, pady=50)
        school_diaries_rectangle.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # Create the label for The School Diaries
        school_label_font = font.Font(family="Helvetica bold", size=45, weight="bold")
        school_diaries_label = tk.Label(school_diaries_rectangle, text="The School Diaries", fg="white", bg="#2F4D99",
                                        font=school_label_font)
        school_diaries_label.pack(pady=(0, 90))

        # Create the frame for buttons
        button_frame = tk.Frame(school_diaries_rectangle, bg="#2F4D99")
        button_frame.pack()

        # Create the School button
        button_font = font.Font(family="Helvetica bold", size=20, weight="bold")
        school_button = tk.Button(button_frame, text="SCHOOL", bg="#698ED4", fg="white", width=10, font=button_font,
                                  command=self.open_school)
        school_button.pack(side=tk.LEFT, padx=(0, 100))

        # Remove button animation
        school_button.configure(activebackground="#698ED4", activeforeground="white")

        # Create the Student button
        student_button = tk.Button(button_frame, text="STUDENT", bg="#698ED4", fg="white", width=10, font=button_font,
                                   command=self.open_student)
        student_button.pack(side=tk.LEFT, padx=(100, 0))

        # Remove button animation
        student_button.configure(activebackground="#698ED4", activeforeground="white")

    def open_school(self):
        new_win = tk.Toplevel(self.window)
        new_obj = School(new_win)

    def open_student(self):
        new_win = tk.Toplevel(self.window)
        new_obj = Student(new_win)


if __name__ == "__main__":
    window = tk.Tk()
    obj = IMS(window)
    window.mainloop()
