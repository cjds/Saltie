from tkinter import *
import ast
from trainer.utils import random_packet_creator
from conversions.input import tensorflow_input_formatter
import tensorflow as tf
from models.actor_critic import tutorial_model
from modelHelpers.actions import action_factory

# Some values useful for editing how the net gets shown
x_spacing = 100
y_spacing = 50
split_spacing = 220
circle_dia = 30


class Visualiser:
    gui = None  # The window
    act_type = None  # Array with activation type for each layer
    big_relu = 20  # The
    big_weight = 30
    layer_activations = None  # The values for the activations
    scale = 1.0  # The current scale of the canvas
    delta = 0.75  # The impact of scrolling
    biggestarraylen = 0  # For aligning all the layers
    eFrame = None  # The frame with the customisation
    iFrame = None  # The frame with the info
    cFrame = None  # The frame with the canvas
    canvas = None  # The canvas showing the net
    rotate_canvas = False  # Should the canvas be rotated

    info_text_neuron = None  # The info about the last neuron hovered over
    info_text_line = None  # The info about the last line (connection) hovered over

    input_array = None  # The StringVar storing the array used when hitting generate
    input_relu = None  # The StringVar storing the array used for the relu adaption
    relu_number = None  # The IntVar storing the spinbox value

    def __init__(self, sess, m, inp=None):
        # Initialising the window
        self.gui = Tk()
        self.gui.geometry('600x600')
        self.gui.title("Net visualisation")

        # Initialising all variables
        self.big_relu = 1
        self.big_weight = 1

        self.model = m
        self.model_info = self.model.get_variables_activations()
        self.n_layers = len(self.model_info)

        self.act_type = [[self.model_info[i][n][2] for n in range(len(self.model_info[i]))] for i in range(self.n_layers)]
        self.randomiser = random_packet_creator.TensorflowPacketGenerator(1)
        self.input_formatter = tensorflow_input_formatter.TensorflowInputFormatter(0, 0, 1, None)
        first_input = self.model.sess.run(self.input_formatter.create_input_array(self.randomiser.get_random_array()))
        self.layer_activations = inp if inp is not None else self.model.get_activations(first_input)

        self.last_layer = list()
        for layer in range(len(self.layer_activations)):
            for split in range(len(self.layer_activations[layer])):
                new_array_size = len(self.get_activations(layer, split)) * len(self.layer_activations[layer])
                if new_array_size > self.biggestarraylen:
                    self.biggestarraylen = new_array_size

        self.biggest_split = 0
        for item in self.model_info:
            if len(item) > self.biggest_split:
                self.biggest_split = len(item)

        self.current_split_layer = 0


        # Initialising the frames
        self.eFrame = Frame(self.gui)
        self.eFrame.grid(row=0, column=0)
        self.iFrame = Frame(self.gui)
        self.iFrame.grid(row=1, column=0, sticky='nw')
        self.cFrame = Frame(self.gui, bd=1, relief=SUNKEN)
        self.cFrame.grid(row=0, column=1, sticky='nsew', rowspan=2)

        self.config_options()

        self.canvas_stuff()
        self.edit_stuff()
        self.info_stuff()
        mainloop()

    def edit_stuff(self):
        self.input_array = StringVar()
        input_array_field = Entry(self.eFrame, textvariable=self.input_array)
        input_array_field.bind('<Return>', lambda event: self.change_input())
        input_array_field.grid(row=0, column=0)
        input_array_button = Button(self.eFrame, command=self.change_input, text="Use data")
        input_array_button.grid(row=0, column=1)

        self.relu_number = IntVar()
        self.relu_number.set(20)
        relu_spin_box = Spinbox(self.eFrame, from_=1, to=1000, width=5, textvariable=self.relu_number)
        relu_spin_box.bind('<Return>', lambda event: self.change_relu_factor())
        relu_spin_box.grid(row=1, column=0)
        relu_button = Button(self.eFrame, command=self.change_relu_factor, text="Change big relu")
        relu_button.grid(row=1, column=1)

        rotate = Button(self.eFrame, command=self.rotate_and_refresh, text="Rotate")
        rotate.grid(row=2, column=0)

        random = Button(self.eFrame, command=self.layer_activations_random, text="Random input")
        random.grid(row=2, column=1)

    def info_stuff(self):
        self.info_text_neuron = StringVar()
        self.info_text_neuron.set("Index: ?, ?\nActivation type: ?\nActivation: ?")
        activation_label = Label(self.iFrame, textvariable=self.info_text_neuron, justify=LEFT)
        activation_label.grid(row=0, column=0, sticky='w')

        self.info_text_line = StringVar()
        self.info_text_line.set("?, ? -> ?, ?")
        activation_label = Label(self.iFrame, textvariable=self.info_text_line, justify=LEFT)
        activation_label.grid(row=1, column=0, sticky='w')

    def canvas_stuff(self):
        # Create canvas including the scrollbars
        class AutoScrollbar(Scrollbar):
            def set(self, lo, hi):
                if float(lo) <= 0.0 and float(hi) >= 1.0:
                    self.grid_remove()
                else:
                    self.grid()
                Scrollbar.set(self, lo, hi)

        def wheel(event):
            scale = 1.0
            # Respond to Linux (event.num) or Windows (event.delta) wheel event
            if event.num == 5 or event.delta == -120:
                scale *= self.delta
                self.scale *= self.delta
            if event.num == 4 or event.delta == 120:
                scale /= self.delta
                self.scale /= self.delta
            # Rescale all canvas objects
            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)
            self.canvas.scale('all', x, y, scale, scale)
            self.canvas.configure(scrollregion=self.canvas.bbox('all'))

        vbar = AutoScrollbar(self.cFrame, orient='vertical')
        hbar = AutoScrollbar(self.cFrame, orient='horizontal')
        vbar.grid(row=0, column=1, sticky='ns')
        hbar.grid(row=1, column=0, sticky='we')
        self.canvas = Canvas(self.cFrame, xscrollcommand=hbar.set, yscrollcommand=vbar.set)
        self.canvas.grid(row=0, column=0, sticky='nsew')
        vbar.configure(command=self.canvas.yview)  # bind scrollbars to the canvas
        hbar.configure(command=self.canvas.xview)

        # Bind events to the Canvas
        self.canvas.bind('<Button-1>', lambda event: self.canvas.scan_mark(event.x, event.y))
        self.canvas.bind('<B1-Motion>', lambda event: self.canvas.scan_dragto(event.x, event.y, gain=1))
        self.canvas.bind('<MouseWheel>', wheel)
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

        # Generate the canvas itself
        if self.layer_activations is not None:
            self.refresh_canvas()

    def create_circle(self, x0, y0, activation, type, layer_index, split_index, neuron):
        if self.rotate_canvas:
            x0, y0 = y0, x0
        if type == 'relu':
            activation = activation if activation <= self.big_relu else self.big_relu
            rgb = int(-1 * (activation - self.big_relu) * 255.0 / self.big_relu)
        else:
            activation = activation if activation <= 1 else 1
            rgb = int(-1 * (activation - 1) * 255)
        hex_color = "#{:02x}{:02x}{:02x}".format(rgb, rgb, rgb)
        tag = str(layer_index) + ";" + str(split_index) + ";" + str(neuron)
        self.canvas.create_oval(x0, y0, x0 + circle_dia, y0 + circle_dia, fill=hex_color, tags=tag)

        def handler(event, la=layer_index, sp=split_index, ne=neuron):
            self.info_text_neuron.set("Index: " + str(la) + ", " + str(ne) + "\nActivation type: " + (
                "Relu" if self.act_type[layer_index] is 'relu' else "Sigmoid") + "\nActivation: " +
                                      str(self.get_activations(la, sp)[ne]))

        self.canvas.tag_bind(tag, "<Motion>", handler)

    def create_line(self, x0, y0, x1, y1, split_index, previous_layer, previous_neuron, current_layer, current_neuron):
        if self.rotate_canvas:
            x0, y0, x1, y1 = y0, x0, y1, x1
        half = .5 * circle_dia

        layer_variables = self.model_info[current_layer][split_index]
        weight_variable = layer_variables[0]
        if len(weight_variable) <= previous_neuron:
            # print('tooo large axis 0', previous_neuron, len(weight_variable))
            return
        previous_weights = weight_variable[previous_neuron]
        if len(previous_weights) <= current_neuron:
            # print('tooo large axis 1', current_neuron, len(previous_weights))
            return
        weight = previous_weights[current_neuron]
        r, g, b = 0, 0, 0
        if abs(weight) <= 0.1:
            return
        if weight >= 0:
            weight = weight if weight <= self.big_weight else self.big_weight
            r = int(weight * 255.0 / self.big_weight)
        else:
            weight = weight if weight >= (-self.big_weight) else (-self.big_weight)
            b = int(-1 * weight * 255 / self.big_weight)

        hex_color = "#{:02x}{:02x}{:02x}".format(r, g, b)

        tag = str(previous_layer) + ";" + str(previous_neuron) + ";" + str(current_layer) + ";" + str(current_neuron)
        self.canvas.create_line(x0 + half, y0 + half, x1 + half, y1 + half, fill=hex_color, tags=tag)

        def handler(event, l0=previous_layer, n0=previous_neuron, l1=current_layer, n1=current_neuron, w=weight):
            self.info_text_line.set(str(l0) + ", " + str(n0) + " -> " + str(l1) + ", " + str(n1) +
                                    "\nWeight: " + str(w))

        self.canvas.tag_bind(tag, "<Motion>", handler)
        self.canvas.tag_lower(tag)

    def create_layer(self, layer_index, split_index, last_layer):
        activations = self.get_activations(layer_index, split_index)
        x = layer_index * x_spacing
        vertical_y = (self.biggestarraylen - len(activations) * split_index) / 2.0
        y = (vertical_y * y_spacing) * .5 - split_spacing * split_index
        this_layer = list()
        for neuron_index, activation in enumerate(activations):
            this_layer.append([x, y])
            if layer_index != 0:
                pass
                #for last_neuron_index, last_neuron in enumerate(last_layer):
                #    self.create_line(last_neuron[0], last_neuron[1], x, y,
                #                     split_index, layer_index - 1, last_neuron_index, layer_index, neuron_index)
            self.create_circle(x, y, activation, self.act_type[layer_index], layer_index, split_index, neuron_index)
            y += y_spacing
        return this_layer

    def refresh_canvas(self):
        self.canvas.scale('all', 0, 0, 1, 1)
        self.scale = 1
        self.canvas.delete('all')
        last_layer = [[]]
        for layer_index in range(len(self.layer_activations)):
            print('adding layer', layer_index)
            current_layer = []
            if len(self.layer_activations[layer_index]) > len(last_layer):
                last_layer = last_layer * len(self.layer_activations[layer_index])
            for split_index in range(len(self.layer_activations[layer_index])):
                print('adding split', split_index)
                output = self.create_layer(layer_index, split_index, last_layer[split_index])
                current_layer.append(output)
            last_layer = current_layer

    def rotate_and_refresh(self):
        self.rotate_canvas = not self.rotate_canvas
        self.refresh_canvas()

    def change_relu_factor(self):
        self.big_relu = self.relu_number.get()
        self.refresh_canvas()

    def change_input(self):
        if self.input_array.get():
            try:
                self.layer_activations = ast.literal_eval(self.input_array.get())
                self.refresh_canvas()
            except Exception:
                pass

    def layer_activations_random(self):
        random_array = self.model.sess.run(self.input_formatter.create_input_array(self.randomiser.get_random_array()))
        self.layer_activations = self.model.get_activations(random_array)
        self.refresh_canvas()

    def config_options(self):
        # Make the canvas expandable
        self.gui.grid_rowconfigure(0, weight=1)
        self.gui.grid_rowconfigure(1, weight=1)
        self.gui.grid_columnconfigure(1, weight=1)
        self.cFrame.grid_rowconfigure(0, weight=1)
        self.cFrame.grid_columnconfigure(0, weight=1)

        self.gui.grid_columnconfigure(0, minsize=100)

    def get_activations(self, layer, split):
        return self.layer_activations[layer][split][0]


if __name__ == '__main__':
    with tf.Session() as sess:
        inp = [[0, 1, 3, 4, 5, 6, 7, 8, 9, 10], [4, 5, 6, 7, 8, 9, 10, 1, 2, 3, 4, 0], [5, 2, 43, 34, 234, 3, 4],
               [5, 7, 2, 5, 7, 19], [1, 0, 0.5, 0.1, 0.6]]
        controls = action_factory.default_scheme
        action_handler = action_factory.get_handler(control_scheme=controls)
        action_handler.get_logit_size()
        model = tutorial_model.TutorialModel(sess, action_handler.get_logit_size(), action_handler=action_handler)
        model.batch_size = 1
        model.mini_batch_size = 1
        model.create_model()
        model.initialize_model()
        Visualiser(sess, model)