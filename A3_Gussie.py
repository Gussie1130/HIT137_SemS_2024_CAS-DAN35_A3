import tkinter as tk
from tkinter import filedialog, messagebox
import cv2
from PIL import Image, ImageTk
import numpy as np

class ImageEditorApp(tk.Tk):
    """
    Image editor main application that integrates image loading, cropping,scaling, filter processing,saving, and undo/redo functions
    """
    def __init__(self):
        super().__init__()
        self.title("Image Editor")  
        
        # Initialize image variables
        self.original_image = None   # Original loaded image（OpenCV，BGR）
        self.modified_image = None   # Modified image (possibly cropped, scaled, or filtered)
        self.base_for_scaling = None # Reference image for scaling operations to avoid distortion from consecutive scaling
        
        # Stack structure for implementing undo and redo (storing copies of the image)
        self.undo_stack = []
        self.redo_stack = []
        
        # Used for crop operations to record the starting coordinates of mouse presses
        self.crop_start = None
        # Used to store the rectangle drawn on the original image canvas id
        self.crop_rect_id = None
        
        # Build menus and interface
        self.setup_menu()
        self.setup_ui()
        self.bind_shortcuts()

    def setup_menu(self):
        """
        Build the menu bar, including the 'File', 'Edit', and 'Filter' menus.
        """
        menu_bar = tk.Menu(self)
        self.config(menu=menu_bar)
        
        # File menu: Open, Save, Exit
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Open (Ctrl+O)", command=self.load_image)
        file_menu.add_command(label="Save (Ctrl+S)", command=self.save_image)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        menu_bar.add_cascade(label="File", menu=file_menu)
        
        # Edit menu: Undo, Redo
        edit_menu = tk.Menu(menu_bar, tearoff=0)
        edit_menu.add_command(label="Undo (Ctrl+Z)", command=self.undo)
        edit_menu.add_command(label="Redo (Ctrl+Y)", command=self.redo)
        menu_bar.add_cascade(label="Edit", menu=edit_menu)
        
        # Filter menu: Grayscale, Edge Detection
        filter_menu = tk.Menu(menu_bar, tearoff=0)
        filter_menu.add_command(label="Grayscale", command=self.apply_grayscale)
        filter_menu.add_command(label="Edge Detection", command=self.apply_edge_detection)
        menu_bar.add_cascade(label="Filters", menu=filter_menu)

    def setup_ui(self):
        """
        Build the interface, including two canvases (original image and modified image), a scaling slider, and other processing buttons.
        """
        # Main frame for placing the left and right canvases
        main_frame = tk.Frame(self)
        main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # Left frame: Display the original image
        left_frame = tk.Frame(main_frame, bd=2, relief=tk.SUNKEN)
        left_frame.pack(side=tk.LEFT, padx=5, pady=5)
        tk.Label(left_frame, text="Original Image").pack()
        self.original_canvas = tk.Canvas(left_frame, cursor="cross")
        self.original_canvas.pack()
        # Bind mouse events to enable drawing of the cropping area
        self.original_canvas.bind("<ButtonPress-1>", self.start_crop)
        self.original_canvas.bind("<B1-Motion>", self.update_crop_rect)
        self.original_canvas.bind("<ButtonRelease-1>", self.end_crop)
        
        # Right frame: Display the modified image
        right_frame = tk.Frame(main_frame, bd=2, relief=tk.SUNKEN)
        right_frame.pack(side=tk.LEFT, padx=5, pady=5)
        tk.Label(right_frame, text="Modified Image").pack()
        self.modified_canvas = tk.Canvas(right_frame)
        self.modified_canvas.pack()
        
        # Bottom frame: Place the scaling slider and other processing buttons
        bottom_frame = tk.Frame(self)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        
        # Scaling slider: Controls the image scaling ratio（10% ~ 200%）
        tk.Label(bottom_frame, text="Scale (%)").pack(side=tk.LEFT)
        self.scale_slider = tk.Scale(bottom_frame, from_=10, to=200, orient=tk.HORIZONTAL, command=self.update_scale)
        self.scale_slider.set(100)  # Default 100%
        self.scale_slider.pack(side=tk.LEFT, padx=5)
        # Bind mouse release event
        self.scale_slider.bind("<ButtonRelease-1>", self.commit_scale)
        
        # Other image processing buttons: Grayscale, Edge Detection
        self.gray_button = tk.Button(bottom_frame, text="Grayscale", command=self.apply_grayscale)
        self.gray_button.pack(side=tk.LEFT, padx=5)
        self.edge_button = tk.Button(bottom_frame, text="Edge Detection", command=self.apply_edge_detection)
        self.edge_button.pack(side=tk.LEFT, padx=5)

    def bind_shortcuts(self):
        """
        Bind keyboard shortcuts for common operations:
        Ctrl+O：Open image
        Ctrl+S：save image
        Ctrl+Z：undo
        Ctrl+Y：redo
        """
        self.bind_all("<Control-o>", lambda event: self.load_image())
        self.bind_all("<Control-s>", lambda event: self.save_image())
        self.bind_all("<Control-z>", lambda event: self.undo())
        self.bind_all("<Control-y>", lambda event: self.redo())

    def load_image(self):
        """
        Load an image through a file dialog and update the display on the interface.
        """
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.gif *.tiff")]
        )
        if not file_path:
            return
        image = cv2.imread(file_path)
        if image is None:
            messagebox.showerror("Error", "Unable to load the image!")
            return
        self.original_image = image
        self.modified_image = image.copy()
        self.base_for_scaling = self.modified_image.copy()
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.display_original_image()
        self.display_modified_image()
        self.scale_slider.set(100)

    def save_image(self):
        """
        Save the modified image to a local file.
        """
        if self.modified_image is None:
            messagebox.showwarning("Warning", "No image to save!")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg;*.jpeg"), ("BMP", "*.bmp"), ("All Files", "*.*")]
        )
        if not file_path:
            return
        success = cv2.imwrite(file_path, self.modified_image)
        if success:
            messagebox.showinfo("Info", "Image has been saved!")
        else:
            messagebox.showerror("Error", "Failed to save the image!")

    def display_original_image(self):
        """
        Convert the original image and display it on the left canvas.
        """
        if self.original_image is None:
            return
        image_rgb = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
        self.original_photo = ImageTk.PhotoImage(pil_image)
        self.original_canvas.config(width=pil_image.width, height=pil_image.height)
        self.original_canvas.create_image(0, 0, image=self.original_photo, anchor=tk.NW)

    def display_modified_image(self, img=None):
        """
        "Display the modified image (or a specified image) on the right canvas.  
        :param img: Optional parameter; if provided, the specified image will be displayed; otherwise,
         `self.modified_image` will be shown."
        """
        if img is None:
            if self.modified_image is None:
                return
            img = self.modified_image
        if len(img.shape) == 2 or (len(img.shape) == 3 and img.shape[2] == 1):
            pil_image = Image.fromarray(img)
        else:
            image_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(image_rgb)
        self.modified_photo = ImageTk.PhotoImage(pil_image)
        self.modified_canvas.config(width=pil_image.width, height=pil_image.height)
        self.modified_canvas.create_image(0, 0, image=self.modified_photo, anchor=tk.NW)

    def start_crop(self, event):
        """
        Record the starting coordinates when the left mouse button is pressed, used to define the cropping area.
        """
        if self.original_image is None:
            return
        self.crop_start = (event.x, event.y)
        if self.crop_rect_id:
            self.original_canvas.delete(self.crop_rect_id)
            self.crop_rect_id = None

    def update_crop_rect(self, event):
        """
        Update the rectangle display of the cropping area in real-time during mouse drag.
        """
        if self.crop_start is None:
            return
        x0, y0 = self.crop_start
        x1, y1 = event.x, event.y
        if self.crop_rect_id:
            self.original_canvas.delete(self.crop_rect_id)
        self.crop_rect_id = self.original_canvas.create_rectangle(
            x0, y0, x1, y1, outline="red", dash=(2, 2)
        )

    def end_crop(self, event):
        """
        When the left mouse button is released, define the cropping area,
        perform the cropping operation on the original image, update the modified image,
        and save the operation into the undo stack.
        """
        if self.crop_start is None or self.original_image is None:
            return
        x0, y0 = self.crop_start
        x1, y1 = event.x, event.y
        x0, x1 = sorted([x0, x1])
        y0, y1 = sorted([y0, y1])
        if x1 - x0 < 10 or y1 - y0 < 10:
            self.original_canvas.delete(self.crop_rect_id)
            self.crop_rect_id = None
            self.crop_start = None
            return
        cropped = self.original_image[y0:y1, x0:x1].copy()
        if self.modified_image is not None:
            self.undo_stack.append(self.modified_image.copy())
            self.redo_stack.clear()
        self.modified_image = cropped
        self.base_for_scaling = self.modified_image.copy()
        self.display_modified_image()
        self.scale_slider.set(100)
        self.crop_start = None
        self.original_canvas.delete(self.crop_rect_id)
        self.crop_rect_id = None

    def update_scale(self, value):
        """
        Scale the image in real-time based on the current value of the scaling slider, 
        without altering the original modified image.
        """
        if self.modified_image is None:
            return
        scale = float(value) / 100.0
        if self.base_for_scaling is None:
            self.base_for_scaling = self.modified_image.copy()
        new_width = int(self.base_for_scaling.shape[1] * scale)
        new_height = int(self.base_for_scaling.shape[0] * scale)
        scaled = cv2.resize(self.base_for_scaling, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
        self.display_modified_image(scaled)
        self.temp_scaled_image = scaled

    def commit_scale(self, event):
        """
        When the user releases the scaling slider, set the currently scaled image as the new
          modified image and save the state.
        """
        if hasattr(self, 'temp_scaled_image'):
            if self.modified_image is not None:
                self.undo_stack.append(self.modified_image.copy())
                self.redo_stack.clear()
            self.modified_image = self.temp_scaled_image.copy()
            self.base_for_scaling = self.modified_image.copy()
            self.display_modified_image()
            del self.temp_scaled_image

    def apply_grayscale(self):
        """
        Convert the modified image to grayscale, update the display, 
        and save the operation state to support undo.
        """
        if self.modified_image is None:
            return
        self.undo_stack.append(self.modified_image.copy())
        self.redo_stack.clear()
        gray = cv2.cvtColor(self.modified_image, cv2.COLOR_BGR2GRAY)
        gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        self.modified_image = gray_bgr
        self.base_for_scaling = self.modified_image.copy()
        self.display_modified_image()
        self.scale_slider.set(100)

    def apply_edge_detection(self):
        """
        Apply the Canny edge detection filter to the modified image, update the display, 
        and save the operation state to support undo.
        """
        if self.modified_image is None:
            return
        self.undo_stack.append(self.modified_image.copy())
        self.redo_stack.clear()
        gray = cv2.cvtColor(self.modified_image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 100, 200)
        edges_bgr = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        self.modified_image = edges_bgr
        self.base_for_scaling = self.modified_image.copy()
        self.display_modified_image()
        self.scale_slider.set(100)

    def undo(self):
        """
        Undo the last operation, retrieve the state from the undo stack, 
        and save the current state into the redo stack.
        """
        if not self.undo_stack:
            messagebox.showinfo("Info", "No actions to undo!")
            return
        self.redo_stack.append(self.modified_image.copy())
        self.modified_image = self.undo_stack.pop()
        self.base_for_scaling = self.modified_image.copy()
        self.display_modified_image()
        self.scale_slider.set(100)

    def redo(self):
        """
        Redo the last undone operation, retrieve the state from the redo stack, 
        and save the current state into the undo stack.
        """
        if not self.redo_stack:
            messagebox.showinfo("Info", "No actions to redo!")
            return
        self.undo_stack.append(self.modified_image.copy())
        self.modified_image = self.redo_stack.pop()
        self.base_for_scaling = self.modified_image.copy()
        self.display_modified_image()
        self.scale_slider.set(100)

if __name__ == "__main__":
    # Open the application
    app = ImageEditorApp()
    app.mainloop()
