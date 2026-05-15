#!/usr/bin/env python3
"""
T-Shirt Mockup Creator GUI (Tkinter Version)
A cross-platform application for creating t-shirt mockups with live preview.
Uses only Tkinter and Pillow - no GTK dependencies required.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageOps
import os


class TShirtMockupApp:
    def __init__(self, root):
        self.root = root
        self.root.title("T-Shirt Mockup Creator")
        self.root.geometry("1200x800")
        
        # Image storage
        self.tshirt_image = None
        self.tshirt_photo = None
        self.graphic_image = None
        self.graphic_photo = None
        self.graphic_original = None  # Keep original for transformations
        
        # Transform parameters
        self.graphic_scale = 1.0
        self.graphic_offset_x = 0
        self.graphic_offset_y = 0
        self.graphic_rotation = 0
        
        # Drag state
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        
        # Setup UI
        self.setup_ui()
        
        # Bind drag and drop (works on most platforms)
        self.canvas.drop_target_register(tk.DND_ALL)
        self.canvas.bind('<Drop>', self.on_drop)
    
    def setup_ui(self):
        """Initialize the user interface"""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top toolbar
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(toolbar, text="Load T-Shirt Mockup", command=self.load_tshirt).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="Load Graphic", command=self.load_graphic).pack(side=tk.LEFT, padx=5)
        
        self.status_label = ttk.Label(toolbar, text="No images loaded", relief=tk.SUNKEN)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        
        # Content area with canvas and controls
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Canvas for preview
        self.canvas = tk.Canvas(content_frame, bg='#404040', highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bind canvas events
        self.canvas.bind('<ButtonPress-1>', self.on_mouse_press)
        self.canvas.bind('<ButtonRelease-1>', self.on_mouse_release)
        self.canvas.bind('<B1-Motion>', self.on_mouse_drag)
        self.canvas.bind('<MouseWheel>', self.on_mouse_wheel)
        self.canvas.bind('<Configure>', self.on_canvas_resize)
        
        # Control panel
        control_frame = ttk.LabelFrame(content_frame, text="Controls", padding=10)
        control_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        control_frame.configure(width=250)
        control_frame.pack_propagate(False)
        
        # Scale control
        ttk.Label(control_frame, text="Graphic Scale:").pack(anchor=tk.W, pady=(0, 5))
        self.scale_var = tk.DoubleVar(value=1.0)
        self.scale_slider = ttk.Scale(
            control_frame, from_=0.1, to=5.0, variable=self.scale_var,
            orient=tk.HORIZONTAL, command=self.on_scale_changed
        )
        self.scale_slider.pack(fill=tk.X, pady=(0, 15))
        
        # Position X control
        ttk.Label(control_frame, text="Position X:").pack(anchor=tk.W, pady=(0, 5))
        self.pos_x_var = tk.IntVar(value=0)
        self.pos_x_slider = ttk.Scale(
            control_frame, from_=-1000, to=1000, variable=self.pos_x_var,
            orient=tk.HORIZONTAL, command=self.on_pos_x_changed
        )
        self.pos_x_slider.pack(fill=tk.X, pady=(0, 15))
        
        # Position Y control
        ttk.Label(control_frame, text="Position Y:").pack(anchor=tk.W, pady=(0, 5))
        self.pos_y_var = tk.IntVar(value=0)
        self.pos_y_slider = ttk.Scale(
            control_frame, from_=-1000, to=1000, variable=self.pos_y_var,
            orient=tk.HORIZONTAL, command=self.on_pos_y_changed
        )
        self.pos_y_slider.pack(fill=tk.X, pady=(0, 15))
        
        # Rotation control
        ttk.Label(control_frame, text="Rotation (degrees):").pack(anchor=tk.W, pady=(0, 5))
        self.rot_var = tk.IntVar(value=0)
        self.rot_slider = ttk.Scale(
            control_frame, from_=-180, to=180, variable=self.rot_var,
            orient=tk.HORIZONTAL, command=self.on_rotation_changed
        )
        self.rot_slider.pack(fill=tk.X, pady=(0, 15))
        
        # Buttons
        ttk.Button(control_frame, text="Reset Position & Scale", 
                   command=self.on_reset).pack(fill=tk.X, pady=5)
        
        ttk.Button(control_frame, text="Process Mockup", 
                   command=self.on_process, style='Accent.TButton').pack(fill=tk.X, pady=(20, 5))
        
        # Instructions
        instructions = ttk.Label(
            control_frame, 
            text="Instructions:\n• Drag & drop images or use buttons\n• Drag graphic to reposition\n• Scroll to zoom in/out\n• Use sliders for fine tuning\n• Click 'Process Mockup' when ready",
            justify=tk.LEFT
        )
        instructions.pack(side=tk.BOTTOM, pady=(20, 0))
        
        # Style for accent button
        style = ttk.Style()
        style.configure('Accent.TButton', font=('Arial', 10, 'bold'))
    
    def load_tshirt(self):
        """Load t-shirt mockup image"""
        filename = filedialog.askopenfilename(
            title="Select T-Shirt Mockup",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.load_tshirt_image(filename)
    
    def load_graphic(self):
        """Load graphic image"""
        filename = filedialog.askopenfilename(
            title="Select Graphic",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.load_graphic_image(filename)
    
    def load_tshirt_image(self, filename):
        """Load t-shirt image from file"""
        try:
            self.tshirt_image = Image.open(filename)
            self.tshirt_image = ImageOps.exif_transpose(self.tshirt_image)  # Handle EXIF rotation
            self.update_preview()
            self.update_status()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load t-shirt image: {e}")
    
    def load_graphic_image(self, filename):
        """Load graphic image from file"""
        try:
            self.graphic_original = Image.open(filename)
            self.graphic_original = ImageOps.exif_transpose(self.graphic_original)
            
            # Convert to RGBA for transparency support
            if self.graphic_original.mode != 'RGBA':
                self.graphic_original = self.graphic_original.convert('RGBA')
            
            self.graphic_image = self.graphic_original.copy()
            
            # Center the graphic initially
            if self.tshirt_image:
                tshirt_w, tshirt_h = self.tshirt_image.size
                graphic_w, graphic_h = self.graphic_original.size
                self.graphic_offset_x = (tshirt_w - graphic_w) // 2
                self.graphic_offset_y = (tshirt_h - graphic_h) // 2
                
                # Update sliders
                self.pos_x_var.set(self.graphic_offset_x)
                self.pos_y_var.set(self.graphic_offset_y)
            
            self.update_preview()
            self.update_status()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load graphic: {e}")
    
    def on_drop(self, event):
        """Handle drag and drop of files"""
        # Parse the dropped file path
        data = event.data
        if data.startswith('{') and data.endswith('}'):
            data = data[1:-1]
        
        if os.path.isfile(data):
            if not self.tshirt_image:
                self.load_tshirt_image(data)
            else:
                self.load_graphic_image(data)
    
    def update_status(self):
        """Update status label"""
        parts = []
        if self.tshirt_image:
            parts.append(f"T-Shirt: {os.path.basename(self.tshirt_image.filename if hasattr(self.tshirt_image, 'filename') else 'loaded')}")
        if self.graphic_original:
            parts.append(f"Graphic: {os.path.basename(self.graphic_original.filename if hasattr(self.graphic_original, 'filename') else 'loaded')}")
        
        self.status_label.config(text=" | ".join(parts) if parts else "No images loaded")
    
    def update_preview(self):
        """Update the canvas preview"""
        self.canvas.delete("all")
        
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if not self.tshirt_image:
            # Draw placeholder text
            self.canvas.create_text(
                canvas_width // 2, canvas_height // 2,
                text="Drag & drop a t-shirt mockup image here\nor click 'Load T-Shirt Mockup'",
                fill='white', font=('Arial', 16), justify=tk.CENTER
            )
            return
        
        # Resize t-shirt to fit canvas while maintaining aspect ratio
        tshirt_w, tshirt_h = self.tshirt_image.size
        scale = min(canvas_width / tshirt_w, canvas_height / tshirt_h, 1.0)
        display_w = int(tshirt_w * scale)
        display_h = int(tshirt_h * scale)
        
        tshirt_resized = self.tshirt_image.resize((display_w, display_h), Image.Resampling.LANCZOS)
        self.tshirt_photo = ImageTk.PhotoImage(tshirt_resized)
        
        # Center t-shirt in canvas
        x_offset = (canvas_width - display_w) // 2
        y_offset = (canvas_height - display_h) // 2
        
        self.canvas.create_image(x_offset, y_offset, anchor=tk.NW, image=self.tshirt_photo)
        
        # Store display scale for coordinate conversion
        self.display_scale = scale
        self.display_offset_x = x_offset
        self.display_offset_y = y_offset
        
        if self.graphic_original:
            # Apply transformations to graphic
            graphic_w, graphic_h = self.graphic_original.size
            scaled_w = int(graphic_w * self.graphic_scale)
            scaled_h = int(graphic_h * self.graphic_scale)
            
            # Resize graphic
            graphic_resized = self.graphic_original.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)
            
            # Rotate graphic
            if self.graphic_rotation != 0:
                graphic_resized = graphic_resized.rotate(-self.graphic_rotation, expand=False, resample=Image.Resampling.BICUBIC)
            
            self.graphic_photo = ImageTk.PhotoImage(graphic_resized)
            
            # Calculate position (convert from image coordinates to display coordinates)
            disp_x = self.display_offset_x + int(self.graphic_offset_x * self.display_scale)
            disp_y = self.display_offset_y + int(self.graphic_offset_y * self.display_scale)
            
            # Draw graphic
            self.canvas.create_image(disp_x, disp_y, anchor=tk.NW, image=self.graphic_photo)
            
            # Draw selection border
            final_w, final_h = graphic_resized.size
            self.canvas.create_rectangle(
                disp_x, disp_y, disp_x + final_w, disp_y + final_h,
                outline='#00ff00', width=2, dash=(5, 3)
            )
    
    def on_canvas_resize(self, event):
        """Handle canvas resize"""
        if self.tshirt_image:
            self.root.after(100, self.update_preview)
    
    def on_mouse_press(self, event):
        """Handle mouse button press"""
        if self.graphic_original:
            # Check if click is within graphic bounds (in display coordinates)
            graphic_w, graphic_h = self.graphic_original.size
            scaled_w = int(graphic_w * self.graphic_scale)
            scaled_h = int(graphic_h * self.graphic_scale)
            
            disp_x = self.display_offset_x + int(self.graphic_offset_x * self.display_scale)
            disp_y = self.display_offset_y + int(self.graphic_offset_y * self.display_scale)
            
            if (disp_x <= event.x <= disp_x + scaled_w and
                disp_y <= event.y <= disp_y + scaled_h):
                self.dragging = True
                self.drag_start_x = event.x
                self.drag_start_y = event.y
    
    def on_mouse_release(self, event):
        """Handle mouse button release"""
        self.dragging = False
    
    def on_mouse_drag(self, event):
        """Handle mouse drag"""
        if self.dragging and self.graphic_original:
            dx = (event.x - self.drag_start_x) / self.display_scale
            dy = (event.y - self.drag_start_y) / self.display_scale
            
            self.graphic_offset_x += dx
            self.graphic_offset_y += dy
            
            # Update sliders
            self.pos_x_var.set(int(self.graphic_offset_x))
            self.pos_y_var.set(int(self.graphic_offset_y))
            
            self.drag_start_x = event.x
            self.drag_start_y = event.y
            
            self.update_preview()
    
    def on_mouse_wheel(self, event):
        """Handle scroll wheel for zooming"""
        if self.graphic_original:
            if event.delta > 0:
                self.graphic_scale = min(5.0, self.graphic_scale + 0.1)
            else:
                self.graphic_scale = max(0.1, self.graphic_scale - 0.1)
            
            self.scale_var.set(round(self.graphic_scale, 2))
            self.update_preview()
    
    def on_scale_changed(self, value):
        """Handle scale slider change"""
        self.graphic_scale = float(value)
        self.update_preview()
    
    def on_pos_x_changed(self, value):
        """Handle X position slider change"""
        self.graphic_offset_x = int(float(value))
        self.update_preview()
    
    def on_pos_y_changed(self, value):
        """Handle Y position slider change"""
        self.graphic_offset_y = int(float(value))
        self.update_preview()
    
    def on_rotation_changed(self, value):
        """Handle rotation slider change"""
        self.graphic_rotation = int(float(value))
        self.update_preview()
    
    def on_reset(self):
        """Reset position and scale"""
        if self.graphic_original and self.tshirt_image:
            tshirt_w, tshirt_h = self.tshirt_image.size
            graphic_w, graphic_h = self.graphic_original.size
            
            self.graphic_scale = 1.0
            self.graphic_offset_x = (tshirt_w - graphic_w) // 2
            self.graphic_offset_y = (tshirt_h - graphic_h) // 2
            self.graphic_rotation = 0
            
            # Update sliders
            self.scale_var.set(1.0)
            self.pos_x_var.set(self.graphic_offset_x)
            self.pos_y_var.set(self.graphic_offset_y)
            self.rot_var.set(0)
            
            self.update_preview()
    
    def on_process(self):
        """Process and export the mockup"""
        if not self.tshirt_image or not self.graphic_original:
            messagebox.showwarning("Warning", "Please load both a t-shirt mockup and a graphic first.")
            return
        
        try:
            # Create a copy of the t-shirt
            result = self.tshirt_image.copy()
            
            # Apply transformations to graphic
            graphic_w, graphic_h = self.graphic_original.size
            scaled_w = int(graphic_w * self.graphic_scale)
            scaled_h = int(graphic_h * self.graphic_scale)
            
            graphic_transformed = self.graphic_original.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)
            
            if self.graphic_rotation != 0:
                graphic_transformed = graphic_transformed.rotate(-self.graphic_rotation, expand=False, resample=Image.Resampling.BICUBIC)
            
            # Paste graphic onto t-shirt
            result.paste(graphic_transformed, (int(self.graphic_offset_x), int(self.graphic_offset_y)), graphic_transformed)
            
            # Ask for save location
            filename = filedialog.asksaveasfilename(
                title="Save Mockup",
                defaultextension=".png",
                filetypes=[
                    ("PNG files", "*.png"),
                    ("JPEG files", "*.jpg"),
                    ("All files", "*.*")
                ]
            )
            
            if filename:
                # Save the result
                if filename.lower().endswith('.jpg') or filename.lower().endswith('.jpeg'):
                    # Convert to RGB for JPEG
                    if result.mode == 'RGBA':
                        background = Image.new('RGB', result.size, (255, 255, 255))
                        background.paste(result, mask=result.split()[3])
                        result = background
                    result.save(filename, 'JPEG', quality=95)
                else:
                    result.save(filename, 'PNG')
                
                messagebox.showinfo("Success", f"Mockup saved to:\n{filename}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process mockup: {e}")


def main():
    root = tk.Tk()
    
    # Try to enable drag and drop (works on Windows and some Linux)
    try:
        from tkinter import dnd
        root.tk.eval('''
            proc load_file {file} {
                puts $file
            }
        ''')
    except:
        pass
    
    app = TShirtMockupApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
