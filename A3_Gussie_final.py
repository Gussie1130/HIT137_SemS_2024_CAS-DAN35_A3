"""
HIT137 - Group Assignment 3
Image Editor Application

Group: CAS/DAN 35
Team Members:
- Aashish (S385593)
- Xueqin Guo (S367175)
- Syed Omar Faruk ()
- Rohan Baniya ()

This program demonstrates an image editor application with functionalities such as:
- Image Loading: Select and load images from the local device and display them in the application window.
- Image Cropping: Draw a rectangle using mouse interaction for image cropping and provide real-time visual feedback.
- Image Resizing: Slider control for resizing the cropped image with real-time updates.
- Saving the Modified Image: Allow saving of the modified image in various formats.

Bonus Features include keyboard shortcuts, grayscale, edge detection, and undo/redo functionality.

"""
import tkinter as tk
from tkinter import filedialog, messagebox
import cv2
from PIL import Image, ImageTk
import numpy as np

class ImageEditorApp(tk.Tk):
    """
    Image editor main application that integrates image loading, cropping,scaling, filter processing,saving, and undo/redo functions.
    """
    def __init__(self):
        super().__init__()
        self.title("Image Editor")  
        
        # Initialize image variables
        self.original_image = None   # Original loaded image（OpenCV，BGR）
        self.modified_image = None   # Modified image (possibly cropped, scaled, or filtered)
        self.base_for_scaling = None # Reference image for scaling operations to avoid distortion from consecutive scaling
        
        # Image display-related parameters
        self.original_display_width = 0    # Display width of the original image on the canvas
        self.original_display_height = 0   # Display height of the original image on the canvas
        self.original_image_width = 0      # Actual width of the original image
        self.original_image_height = 0     # Actual height of the original image
        
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
        """Build the menu bar, including the 'File', 'Edit', and 'Filter' menus."""
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
        """构Build the interface, including two canvases (original image and modified image), a scaling slider, and other processing buttons."""
        # Main frame for placing the left and right canvases
        main_frame = tk.Frame(self)
        main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # Left frame: original image (with fixed size)
        left_frame = tk.Frame(main_frame, bd=2, relief=tk.SUNKEN)
        left_frame.pack(side=tk.LEFT, padx=5, pady=5)
        tk.Label(left_frame, text="Original Image").pack()
        self.original_canvas = tk.Canvas(left_frame, cursor="cross", width=400, height=400)
        self.original_canvas.pack()
        self.original_canvas.bind("<ButtonPress-1>", self.start_crop)
        self.original_canvas.bind("<B1-Motion>", self.update_crop_rect)
        self.original_canvas.bind("<ButtonRelease-1>", self.end_crop)
        
        # Right frame: modified image (with scroll bar)
        right_frame = tk.Frame(main_frame, bd=2, relief=tk.SUNKEN)
        right_frame.pack(side=tk.LEFT, padx=5, pady=5)
        tk.Label(right_frame, text="Modified Image").pack()
        
        # Add scroll bar
        h_scroll = tk.Scrollbar(right_frame, orient=tk.HORIZONTAL)
        v_scroll = tk.Scrollbar(right_frame, orient=tk.VERTICAL)
        self.modified_canvas = tk.Canvas(right_frame, width=400, height=400,
                                       xscrollcommand=h_scroll.set,
                                       yscrollcommand=v_scroll.set)
        h_scroll.config(command=self.modified_canvas.xview)
        v_scroll.config(command=self.modified_canvas.yview)
        
        self.modified_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Bottom frame: Place the scaling slider and other processing buttons
        bottom_frame = tk.Frame(self)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        
        # "Scaling slider"
        tk.Label(bottom_frame, text="Scale (%)").pack(side=tk.LEFT)
        self.scale_slider = tk.Scale(bottom_frame, from_=10, to=200, orient=tk.HORIZONTAL, command=self.update_scale)
        self.scale_slider.set(100)
        self.scale_slider.pack(side=tk.LEFT, padx=5)
        self.scale_slider.bind("<ButtonRelease-1>", self.commit_scale)
        
        # Function buttons
        self.gray_button = tk.Button(bottom_frame, text="Grayscale", command=self.apply_grayscale)
        self.gray_button.pack(side=tk.LEFT, padx=5)
        self.edge_button = tk.Button(bottom_frame, text="Edge Detection", command=self.apply_edge_detection)
        self.edge_button.pack(side=tk.LEFT, padx=5)

    def bind_shortcuts(self):
        """Bind keyboard shortcuts."""
        self.bind_all("<Control-o>", lambda event: self.load_image())
        self.bind_all("<Control-s>", lambda event: self.save_image())
        self.bind_all("<Control-z>", lambda event: self.undo())
        self.bind_all("<Control-y>", lambda event: self.redo())

    def load_image(self):
        """Load image file and initialize relevant parameters.。"""
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.gif *.tiff")]
        )
        if not file_path:
            return
        image = cv2.imread(file_path)
        if image is None:
            messagebox.showerror("Error", "Unable to load image!")
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
        """Save the modified image to a file.。"""
        if self.modified_image is None:
            messagebox.showwarning("Warning", "No image to save!")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.gif *.tiff")]
        )
        if not file_path:
            return
        success = cv2.imwrite(file_path, self.modified_image)
        if success:
            messagebox.showinfo("Information", "Image saved successfully!")
        else:
            messagebox.showerror("Error", "Failed to save image!")


    def display_original_image(self):
        """Display the original image (automatically scaled to fit the canvas).。"""
        if self.original_image is None:
            return
        image_rgb = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
        
        # Calculate the scaling ratio to fit the canvas.
        canvas_width = self.original_canvas.winfo_width()
        canvas_height = self.original_canvas.winfo_height()
        image_width, image_height = pil_image.size
        scale = min(canvas_width / image_width, canvas_height / image_height)
        
        # Store the original image and display dimensions for coordinate transformation
        self.original_image_width = image_width
        self.original_image_height = image_height
        self.original_display_width = int(image_width * scale)
        self.original_display_height = int(image_height * scale)
        
        # Scale and display
        pil_image = pil_image.resize((self.original_display_width, self.original_display_height), Image.Resampling.LANCZOS)
        self.original_photo = ImageTk.PhotoImage(pil_image)
        self.original_canvas.create_image(0, 0, image=self.original_photo, anchor=tk.NW)

    def display_modified_image(self, img=None):
        """
        - When the `img` parameter is `None`, display the current `modified_image` (automatically scaled to fit the canvas)
        - When the `img` parameter is provided, display it in its original dimensions
        """
        if img is None:
            if self.modified_image is None:
                return
            img = self.modified_image.copy()
            # Adaptive scaling display
            if len(img.shape) == 2 or (len(img.shape) == 3 and img.shape[2] == 1):
                pil_image = Image.fromarray(img)
            else:
                pil_image = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            
            # Calculate the scaling ratio to fit the canvas
            canvas_width = self.modified_canvas.winfo_width()
            canvas_height = self.modified_canvas.winfo_height()
            image_width, image_height = pil_image.size
            scale = min(canvas_width / image_width, canvas_height / image_height)
            
            # Scale and display
            new_width = int(image_width * scale)
            new_height = int(image_height * scale)
            pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(pil_image)
            self.modified_canvas.delete("all")
            self.modified_canvas.create_image(0, 0, image=photo, anchor=tk.NW)
            self.modified_photo = photo  # Maintain reference to avoid garbage collection
        else:
            # Display the original dimensions during real-time scaling preview
            if len(img.shape) == 2 or (len(img.shape) == 3 and img.shape[2] == 1):
                pil_image = Image.fromarray(img)
            else:
                pil_image = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            photo = ImageTk.PhotoImage(pil_image)
            self.modified_canvas.delete("all")
            self.modified_canvas.create_image(0, 0, image=photo, anchor=tk.NW)
            self.modified_canvas.config(scrollregion=self.modified_canvas.bbox(tk.ALL))  # Update the scroll region
            self.modified_photo = photo  # Maintain reference

    def start_crop(self, event):
        """Start the cropping operation and record the starting coordinates"""
        if self.original_image is None:
            return
        self.crop_start = (event.x, event.y)
        if self.crop_rect_id:
            self.original_canvas.delete(self.crop_rect_id)
            self.crop_rect_id = None

    def update_crop_rect(self, event):
        """Update the display of the cropping rectangle"""
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
        """End the cropping operation and perform the actual crop"""
        if self.crop_start is None or self.original_image is None:
            return
        
        # Get canvas coordinates and constrain them within the display range
        x0 = max(0, min(self.crop_start[0], self.original_display_width))
        y0 = max(0, min(self.crop_start[1], self.original_display_height))
        x1 = max(0, min(event.x, self.original_display_width))
        y1 = max(0, min(event.y, self.original_display_height))
        
        # Convert to original image coordinates
        scale_x = self.original_image_width / self.original_display_width
        scale_y = self.original_image_height / self.original_display_height
        orig_x0 = int(x0 * scale_x)
        orig_y0 = int(y0 * scale_y)
        orig_x1 = int(x1 * scale_x)
        orig_y1 = int(y1 * scale_y)
        
        # Ensure a valid cropping area
        if orig_x1 - orig_x0 < 10 or orig_y1 - orig_y0 < 10:
            self.original_canvas.delete(self.crop_rect_id)
            self.crop_rect_id = None
            self.crop_start = None
            return
        
        # Perform cropping
        cropped = self.original_image[orig_y0:orig_y1, orig_x0:orig_x1].copy()
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
        """Update the scaling preview in real time."""
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
        """Confirm the scaling operation and update the reference image."""
        if hasattr(self, 'temp_scaled_image'):
            if self.modified_image is not None:
                self.undo_stack.append(self.modified_image.copy())
                self.redo_stack.clear()
            self.modified_image = self.temp_scaled_image.copy()
            self.base_for_scaling = self.modified_image.copy()
            self.display_modified_image()  # Use adaptive display after submission
            del self.temp_scaled_image

    def apply_grayscale(self):
        """Apply the grayscale filter."""
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
        """Apply the edge detection filter."""
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
        """Undo the last operation"""
        if not self.undo_stack:
            messagebox.showinfo("Notice", "No operation to undo!")
            return
        self.redo_stack.append(self.modified_image.copy())
        self.modified_image = self.undo_stack.pop()
        self.base_for_scaling = self.modified_image.copy()
        self.display_modified_image()
        self.scale_slider.set(100)

    def redo(self):
        """Redo the last undone operation"""
        if not self.redo_stack:
            messagebox.showinfo("Notice", "No operation to redo!")
            return
        self.undo_stack.append(self.modified_image.copy())
        self.modified_image = self.redo_stack.pop()
        self.base_for_scaling = self.modified_image.copy()
        self.display_modified_image()
        self.scale_slider.set(100)

if __name__ == "__main__":
    app = ImageEditorApp()
    app.mainloop()
