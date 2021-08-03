import tkinter as tk

class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.pack()
        self.create_widgets()
        self.a = ''
        self.math1 = 0
        self.math2 = 0

    def create_widgets(self):
        self.quit_button = tk.Button(self, text='Q', fg='red', command=self.master.destroy)
        self.quit_button.grid(row=4, column=0, columnspan=4, sticky="we")

        self.c_button = tk.Button(self)
        self.c_button['text'] = 'C'
        self.c_button.command = self.clear_all
        self.c_button.grid(row=3, column=0)

        self.one_button = tk.Button(self)
        self.one_button['text'] = 1
        self.one_button['command'] = self.add_1_to_str
        self.one_button.grid(row=0, column=0)

        self.two_button = tk.Button(self)
        self.two_button['text'] = 2
        self.two_button['command'] = self.add_2_to_str
        self.two_button.grid(row=0, column=1)

        self.three_button = tk.Button(self)
        self.three_button['text'] = 3
        self.three_button['command'] = self.add_3_to_str
        self.three_button.grid(row=0, column=2)

        self.four_button = tk.Button(self)
        self.four_button['text'] = 4
        self.four_button['command'] = self.add_4_to_str
        self.four_button.grid(row=1, column=0)

        self.five_button = tk.Button(self)
        self.five_button['text'] = 5
        self.five_button['command'] = self.add_5_to_str
        self.five_button.grid(row=1, column=1)

        self.six_button = tk.Button(self)
        self.six_button['text'] = 6
        self.six_button['command'] = self.add_6_to_str
        self.six_button.grid(row=1, column=2)

        self.seven_button = tk.Button(self)
        self.seven_button['text'] = 7
        self.seven_button['command'] = self.add_7_to_str
        self.seven_button.grid(row=2, column=0)

        self.eight_button = tk.Button(self)
        self.eight_button['text'] = 8
        self.eight_button['command'] = self.add_8_to_str
        self.eight_button.grid(row=2, column=1)

        self.nine_button = tk.Button(self)
        self.nine_button['text'] = 9
        self.nine_button['command'] = self.add_9_to_str
        self.nine_button.grid(row=2, column=2)

        self.zero_button = tk.Button(self)
        self.zero_button['text'] = 0
        self.zero_button['command'] = self.add_0_to_str
        self.zero_button.grid(row=3, column=2)

        self.equal_button = tk.Button(self)
        self.equal_button['text'] = '='
        self.equal_button['command'] = self.equal
        self.equal_button.grid(row=3, column=1)

        self.plus_button = tk.Button(self)
        self.plus_button['text'] = '+'
        self.plus_button['command'] = self.plus
        self.plus_button.grid(row=0, column=3)

        self.subtract_button = tk.Button(self)
        self.subtract_button['text'] = '-'
        self.subtract_button['command'] = self.subtract
        self.subtract_button.grid(row=1, column=3)

        self.multiply_button = tk.Button(self)
        self.multiply_button['text'] = 'X'
        self.multiply_button['command'] = self.multiply
        self.multiply_button.grid(row=2, column=3)

        self.divide_button = tk.Button(self)
        self.divide_button['text'] = '/'
        self.divide_button['command'] = self.multiply
        self.divide_button.grid(row=3, column=3)

    def plus(self):
        self.operation = '+'
        self.a = int(self.a)
        self.math1 = self.a
        self.a = str(self.a)
        self.a = ''

    def subtract(self):
        self.operation = '-'
        self.a = int(self.a)
        self.math1 = self.a
        self.a = str(self.a)
        self.a = ''

    def multiply(self):
        self.operation = '*'
        self.a = int(self.a)
        self.math1 = self.a
        self.a = str(self.a)
        self.a = ''

    def divide(self):
        self.operation = '/'
        self.a = int(self.a)
        self.math1 = self.a
        self.a = str(self.a)
        self.a = ''

    def equal(self):
        self.math2 = self.a
        self.math1 = int(self.math1)
        self.math2 = int(self.math2)
        if self.operation == '+':
            self.total = self.math1 + self.math2
        elif self.operation == '-':
            self.total = self.math1 - self.math2
        elif self.operation == '*':
            self.total = self.math1 * self.math2
        elif self.operation == '/':
            self.total = self.math1 / self.math2
        self.math1 = str(self.math1)
        self.math2 = str(self.math2)
        self.total = str(self.total)
        print(self.math1 + self.operation + self.math2 + '=' + self.total)

    def add_1_to_str(self):
        self.a = self.a + '1'

    def add_2_to_str(self):
        self.a = self.a + '2'

    def add_3_to_str(self):
        self.a = self.a + '3'

    def add_4_to_str(self):
        self.a = self.a + '4'

    def add_5_to_str(self):
        self.a = self.a + '5'

    def add_6_to_str(self):
        self.a = self.a + '6'

    def add_7_to_str(self):
        self.a = self.a + '7'

    def add_8_to_str(self):
        self.a = self.a + '8'

    def add_9_to_str(self):
        self.a = self.a + '9'

    def add_0_to_str(self):
        self.a = self.a + '0'

    def clear_all(self):
        self.a = '0'
        print(self.a)

root = tk.Tk()
app = Application(master=root)
app.mainloop()
