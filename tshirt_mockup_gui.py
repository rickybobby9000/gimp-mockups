#!/usr/bin/env python3
"""
T-Shirt Mockup Creator GUI
A GIMP 3.2 compatible application for creating t-shirt mockups with live preview.
"""

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Gio
import os
import sys
import math

try:
    from gimpfu import *
    GIMP_AVAILABLE = True
except ImportError:
    GIMP_AVAILABLE = False
    print("Warning: GIMP Python-Fu not available. Running in preview-only mode.")


class TShirtMockupApp(Gtk.Window):
    def __init__(self):
        super().__init__(title="T-Shirt Mockup Creator")
        self.set_default_size(1200, 800)
        self.set_border_width(10)
        
        # Image storage
        self.tshirt_image = None
        self.tshirt_pixbuf = None
        self.graphic_image = None
        self.graphic_pixbuf = None
        
        # Transform parameters
        self.graphic_scale = 1.0
        self.graphic_offset_x = 0
        self.graphic_offset_y = 0
        self.graphic_rotation = 0
        
        # Preview state
        self.preview_surface = None
        self.dragging = False
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        
        self.init_ui()
        self.connect("destroy", Gtk.main_quit)
    
    def init_ui(self):
        """Initialize the user interface"""
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(main_box)
        
        # Top toolbar for loading images
        toolbar_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        main_box.pack_start(toolbar_box, False, False, 0)
        
        # T-shirt load button
        tshirt_btn = Gtk.Button(label="Load T-Shirt Mockup")
        tshirt_btn.connect("clicked", self.on_load_tshirt)
        toolbar_box.pack_start(tshirt_btn, False, False, 0)
        
        # Graphic load button
        graphic_btn = Gtk.Button(label="Load Graphic")
        graphic_btn.connect("clicked", self.on_load_graphic)
        toolbar_box.pack_start(graphic_btn, False, False, 0)
        
        # Status label
        self.status_label = Gtk.Label(label="No images loaded")
        toolbar_box.pack_start(self.status_label, True, True, 0)
        
        # Main content area with drawing canvas and controls
        content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        main_box.pack_start(content_box, True, True, 0)
        
        # Drawing area for preview
        self.drawing_area = Gtk.DrawingArea()
        self.drawing_area.set_size_request(800, 600)
        self.drawing_area.connect("draw", self.on_draw)
        self.drawing_area.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.SCROLL_MASK
        )
        self.drawing_area.connect("button-press-event", self.on_button_press)
        self.drawing_area.connect("button-release-event", self.on_button_release)
        self.drawing_area.connect("motion-notify-event", self.on_motion_notify)
        self.drawing_area.connect("scroll-event", self.on_scroll)
        
        # Enable drag and drop
        self.drawing_area.drag_dest_set(
            Gtk.DestDefaults.ALL,
            [],
            Gdk.DragAction.COPY
        )
        self.drawing_area.drag_dest_add_uri_targets()
        self.drawing_area.connect("drag-data-received", self.on_drag_data_received)
        
        content_box.pack_start(self.drawing_area, True, True, 0)
        
        # Control panel on the right
        control_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        control_box.set_size_request(250, -1)
        content_box.pack_start(control_box, False, False, 0)
        
        # Scale control
        scale_label = Gtk.Label(label="Graphic Scale:")
        scale_label.set_halign(Gtk.Align.START)
        control_box.pack_start(scale_label, False, False, 0)
        
        self.scale_adjustment = Gtk.Adjustment(value=1.0, lower=0.1, upper=5.0, step_increment=0.1, page_increment=0.5)
        self.scale_slider = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.scale_adjustment)
        self.scale_slider.set_digits(2)
        self.scale_slider.connect("value-changed", self.on_scale_changed)
        control_box.pack_start(self.scale_slider, False, False, 0)
        
        # Position X control
        pos_x_label = Gtk.Label(label="Position X:")
        pos_x_label.set_halign(Gtk.Align.START)
        control_box.pack_start(pos_x_label, False, False, 0)
        
        self.pos_x_adjustment = Gtk.Adjustment(value=0, lower=-1000, upper=1000, step_increment=1, page_increment=10)
        self.pos_x_slider = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.pos_x_adjustment)
        self.pos_x_slider.set_digits(0)
        self.pos_x_slider.connect("value-changed", self.on_pos_x_changed)
        control_box.pack_start(self.pos_x_slider, False, False, 0)
        
        # Position Y control
        pos_y_label = Gtk.Label(label="Position Y:")
        pos_y_label.set_halign(Gtk.Align.START)
        control_box.pack_start(pos_y_label, False, False, 0)
        
        self.pos_y_adjustment = Gtk.Adjustment(value=0, lower=-1000, upper=1000, step_increment=1, page_increment=10)
        self.pos_y_slider = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.pos_y_adjustment)
        self.pos_y_slider.set_digits(0)
        self.pos_y_slider.connect("value-changed", self.on_pos_y_changed)
        control_box.pack_start(self.pos_y_slider, False, False, 0)
        
        # Rotation control
        rot_label = Gtk.Label(label="Rotation (degrees):")
        rot_label.set_halign(Gtk.Align.START)
        control_box.pack_start(rot_label, False, False, 0)
        
        self.rot_adjustment = Gtk.Adjustment(value=0, lower=-180, upper=180, step_increment=1, page_increment=15)
        self.rot_slider = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.rot_adjustment)
        self.rot_slider.set_digits(0)
        self.rot_slider.connect("value-changed", self.on_rotation_changed)
        control_box.pack_start(self.rot_slider, False, False, 0)
        
        # Reset button
        reset_btn = Gtk.Button(label="Reset Position & Scale")
        reset_btn.connect("clicked", self.on_reset)
        control_box.pack_start(reset_btn, False, False, 0)
        
        # Process button
        process_btn = Gtk.Button(label="Process Mockup")
        process_btn.get_style_context().add_class("suggested-action")
        process_btn.connect("clicked", self.on_process)
        control_box.pack_end(process_btn, False, False, 0)
        
        # Instructions
        instructions = Gtk.Label()
        instructions.set_markup(
            "<b>Instructions:</b>\n"
            "• Drag & drop images or use buttons\n"
            "• Drag graphic to reposition\n"
            "• Scroll to zoom in/out\n"
            "• Use sliders for fine tuning\n"
            "• Click 'Process Mockup' when ready"
        )
        instructions.set_halign(Gtk.Align.START)
        instructions.set_line_wrap(True)
        control_box.pack_end(instructions, False, False, 0)
    
    def on_load_tshirt(self, widget):
        """Load t-shirt mockup image"""
        dialog = Gtk.FileChooserDialog(
            title="Select T-Shirt Mockup",
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )
        
        filter_img = Gtk.FileFilter()
        filter_img.set_name("Image files")
        filter_img.add_mime_type("image/*")
        dialog.add_filter(filter_img)
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            self.load_tshirt_image(filename)
        
        dialog.destroy()
    
    def on_load_graphic(self, widget):
        """Load graphic image"""
        dialog = Gtk.FileChooserDialog(
            title="Select Graphic",
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )
        
        filter_img = Gtk.FileFilter()
        filter_img.set_name("Image files")
        filter_img.add_mime_type("image/*")
        dialog.add_filter(filter_img)
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            self.load_graphic_image(filename)
        
        dialog.destroy()
    
    def load_tshirt_image(self, filename):
        """Load t-shirt image from file"""
        try:
            self.tshirt_pixbuf = GdkPixbuf.Pixbuf.new_from_file(filename)
            self.tshirt_image = filename
            self.update_status()
            self.queue_preview_update()
        except Exception as e:
            self.show_error(f"Failed to load t-shirt image: {e}")
    
    def load_graphic_image(self, filename):
        """Load graphic image from file"""
        try:
            self.graphic_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                filename, -1, -1, True
            )
            self.graphic_image = filename
            # Center the graphic initially
            if self.tshirt_pixbuf:
                self.graphic_offset_x = (self.tshirt_pixbuf.get_width() - self.graphic_pixbuf.get_width()) // 2
                self.graphic_offset_y = (self.tshirt_pixbuf.get_height() - self.graphic_pixbuf.get_height()) // 2
                self.pos_x_adjustment.set_value(self.graphic_offset_x)
                self.pos_y_adjustment.set_value(self.graphic_offset_y)
            self.update_status()
            self.queue_preview_update()
        except Exception as e:
            self.show_error(f"Failed to load graphic: {e}")
    
    def on_drag_data_received(self, widget, drag_context, x, y, data, info, time):
        """Handle drag and drop of files"""
        uris = data.get_uris()
        if uris:
            uri = uris[0]
            if uri.startswith("file://"):
                filename = uri[7:]  # Remove file:// prefix
                filename = filename.replace("%20", " ")  # Handle spaces
                
                # Check if it's the first image (t-shirt) or second (graphic)
                if not self.tshirt_image:
                    self.load_tshirt_image(filename)
                else:
                    self.load_graphic_image(filename)
    
    def update_status(self):
        """Update status label"""
        status_parts = []
        if self.tshirt_image:
            status_parts.append(f"T-Shirt: {os.path.basename(self.tshirt_image)}")
        if self.graphic_image:
            status_parts.append(f"Graphic: {os.path.basename(self.graphic_image)}")
        
        if status_parts:
            self.status_label.set_text(" | ".join(status_parts))
        else:
            self.status_label.set_text("No images loaded")
    
    def queue_preview_update(self):
        """Queue a preview update"""
        if self.drawing_area:
            self.drawing_area.queue_draw()
    
    def on_draw(self, widget, cr):
        """Draw the preview"""
        # Clear background
        cr.set_source_rgb(0.3, 0.3, 0.3)
        cr.paint()
        
        if not self.tshirt_pixbuf:
            # Draw placeholder text
            cr.set_source_rgb(1.0, 1.0, 1.0)
            cr.select_font_face("Sans", 0, 16)
            cr.move_to(50, 50)
            cr.show_text("Drag & drop a t-shirt mockup image here")
            return
        
        # Draw t-shirt
        Gdk.cairo_set_source_pixbuf(cr, self.tshirt_pixbuf, 0, 0)
        cr.paint()
        
        if self.graphic_pixbuf:
            # Apply transformations to graphic
            cr.save()
            
            # Calculate center of graphic for rotation
            scaled_width = int(self.graphic_pixbuf.get_width() * self.graphic_scale)
            scaled_height = int(self.graphic_pixbuf.get_height() * self.graphic_scale)
            
            center_x = self.graphic_offset_x + scaled_width / 2
            center_y = self.graphic_offset_y + scaled_height / 2
            
            # Translate to center, rotate, translate back
            cr.translate(center_x, center_y)
            cr.rotate(math.radians(self.graphic_rotation))
            cr.translate(-center_x, -center_y)
            
            # Scale and draw graphic
            Gdk.cairo_set_source_pixbuf(cr, self.graphic_pixbuf, 
                                       self.graphic_offset_x, 
                                       self.graphic_offset_y)
            
            pattern = cr.get_source()
            matrix = pattern.get_matrix()
            matrix.scale(1.0 / self.graphic_scale, 1.0 / self.graphic_scale)
            pattern.set_matrix(matrix)
            
            cr.rectangle(self.graphic_offset_x, self.graphic_offset_y, 
                        scaled_width, scaled_height)
            cr.fill()
            
            cr.restore()
            
            # Draw selection border around graphic
            cr.set_source_rgba(0.0, 1.0, 0.0, 0.5)
            cr.set_line_width(2)
            cr.rectangle(self.graphic_offset_x, self.graphic_offset_y, 
                        scaled_width, scaled_height)
            cr.stroke()
    
    def on_button_press(self, widget, event):
        """Handle mouse button press"""
        if event.button == 1 and self.graphic_pixbuf:  # Left click
            scaled_width = int(self.graphic_pixbuf.get_width() * self.graphic_scale)
            scaled_height = int(self.graphic_pixbuf.get_height() * self.graphic_scale)
            
            # Check if click is within graphic bounds
            if (self.graphic_offset_x <= event.x <= self.graphic_offset_x + scaled_width and
                self.graphic_offset_y <= event.y <= self.graphic_offset_y + scaled_height):
                self.dragging = True
                self.last_mouse_x = event.x
                self.last_mouse_y = event.y
    
    def on_button_release(self, widget, event):
        """Handle mouse button release"""
        if event.button == 1:
            self.dragging = False
    
    def on_motion_notify(self, widget, event):
        """Handle mouse motion"""
        if self.dragging and self.graphic_pixbuf:
            dx = event.x - self.last_mouse_x
            dy = event.y - self.last_mouse_y
            
            self.graphic_offset_x += dx
            self.graphic_offset_y += dy
            
            self.pos_x_adjustment.set_value(self.graphic_offset_x)
            self.pos_y_adjustment.set_value(self.graphic_offset_y)
            
            self.last_mouse_x = event.x
            self.last_mouse_y = event.y
            
            self.queue_preview_update()
    
    def on_scroll(self, widget, event):
        """Handle scroll wheel for zooming"""
        if self.graphic_pixbuf:
            if event.direction == Gdk.ScrollDirection.UP:
                self.graphic_scale = min(5.0, self.graphic_scale + 0.1)
            elif event.direction == Gdk.ScrollDirection.DOWN:
                self.graphic_scale = max(0.1, self.graphic_scale - 0.1)
            
            self.scale_adjustment.set_value(self.graphic_scale)
            self.queue_preview_update()
    
    def on_scale_changed(self, widget):
        """Handle scale slider change"""
        self.graphic_scale = widget.get_value()
        self.queue_preview_update()
    
    def on_pos_x_changed(self, widget):
        """Handle X position slider change"""
        self.graphic_offset_x = int(widget.get_value())
        self.queue_preview_update()
    
    def on_pos_y_changed(self, widget):
        """Handle Y position slider change"""
        self.graphic_offset_y = int(widget.get_value())
        self.queue_preview_update()
    
    def on_rotation_changed(self, widget):
        """Handle rotation slider change"""
        self.graphic_rotation = widget.get_value()
        self.queue_preview_update()
    
    def on_reset(self, widget):
        """Reset position and scale to defaults"""
        if self.tshirt_pixbuf and self.graphic_pixbuf:
            self.graphic_scale = 1.0
            self.graphic_offset_x = (self.tshirt_pixbuf.get_width() - self.graphic_pixbuf.get_width()) // 2
            self.graphic_offset_y = (self.tshirt_pixbuf.get_height() - self.graphic_pixbuf.get_height()) // 2
            self.graphic_rotation = 0
            
            self.scale_adjustment.set_value(1.0)
            self.pos_x_adjustment.set_value(self.graphic_offset_x)
            self.pos_y_adjustment.set_value(self.graphic_offset_y)
            self.rot_adjustment.set_value(0)
            
            self.queue_preview_update()
    
    def on_process(self, widget):
        """Process the mockup"""
        if not self.tshirt_image or not self.graphic_image:
            self.show_error("Please load both a t-shirt mockup and a graphic.")
            return
        
        # Save dialog for output
        dialog = Gtk.FileChooserDialog(
            title="Save Mockup",
            parent=self,
            action=Gtk.FileChooserAction.SAVE
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK
        )
        dialog.set_do_overwrite_confirmation(True)
        
        # Set default filename
        base_name = os.path.splitext(os.path.basename(self.tshirt_image))[0]
        dialog.set_current_name(f"{base_name}_mockup.png")
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            output_path = dialog.get_filename()
            self.process_mockup(output_path)
        
        dialog.destroy()
    
    def process_mockup(self, output_path):
        """Process the mockup using GIMP or fallback method"""
        if GIMP_AVAILABLE:
            self.process_with_gimp(output_path)
        else:
            self.process_with_pil(output_path)
    
    def process_with_gimp(self, output_path):
        """Process using GIMP Python-Fu"""
        try:
            # Load images into GIMP
            tshirt_layer = pdb.gimp_file_load_layer(
                self.tshirt_image, 
                os.path.basename(self.tshirt_image)
            )
            graphic_layer = pdb.gimp_file_load_layer(
                self.graphic_image,
                os.path.basename(self.graphic_image)
            )
            
            # Create new image
            width = self.tshirt_pixbuf.get_width()
            height = self.tshirt_pixbuf.get_height()
            image = pdb.gimp_image_new(width, height, 24)
            
            # Add layers
            pdb.gimp_image_insert_layer(image, tshirt_layer, None, 0)
            pdb.gimp_image_insert_layer(image, graphic_layer, None, 0)
            
            # Scale graphic layer
            scaled_width = int(self.graphic_pixbuf.get_width() * self.graphic_scale)
            scaled_height = int(self.graphic_pixbuf.get_height() * self.graphic_scale)
            pdb.gimp_layer_scale(graphic_layer, scaled_width, scaled_height, True)
            
            # Position graphic layer
            pdb.gimp_layer_set_offsets(graphic_layer, 
                                      int(self.graphic_offset_x), 
                                      int(self.graphic_offset_y))
            
            # Rotate if needed
            if self.graphic_rotation != 0:
                pdb.gimp_item_transform_rotate(graphic_layer, 
                                              math.radians(self.graphic_rotation),
                                              True,
                                              scaled_width/2, 
                                              scaled_height/2)
            
            # Merge layers
            merged_layer = pdb.gimp_image_merge_visible_layers(image, 0)
            
            # Export
            pdb.gimp_file_save(image, merged_layer, output_path, output_path)
            
            # Cleanup
            pdb.gimp_image_delete(image)
            
            self.show_info(f"Mockup saved successfully to:\n{output_path}")
            
        except Exception as e:
            self.show_error(f"GIMP processing failed: {e}\n\nTrying fallback method...")
            self.process_with_pil(output_path)
    
    def process_with_pil(self, output_path):
        """Process using PIL/Pillow as fallback"""
        try:
            from PIL import Image
            
            # Load images
            tshirt_img = Image.open(self.tshirt_image).convert("RGBA")
            graphic_img = Image.open(self.graphic_image).convert("RGBA")
            
            # Scale graphic
            scaled_width = int(graphic_img.width * self.graphic_scale)
            scaled_height = int(graphic_img.height * self.graphic_scale)
            graphic_img = graphic_img.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
            
            # Rotate graphic
            if self.graphic_rotation != 0:
                graphic_img = graphic_img.rotate(-self.graphic_rotation, expand=False, resample=Image.Resampling.BICUBIC)
            
            # Create result image
            result = tshirt_img.copy()
            
            # Paste graphic with transparency
            result.paste(graphic_img, 
                        (int(self.graphic_offset_x), int(self.graphic_offset_y)), 
                        graphic_img)
            
            # Save
            result.save(output_path, "PNG")
            
            self.show_info(f"Mockup saved successfully to:\n{output_path}")
            
        except ImportError:
            self.show_error("PIL/Pillow not installed. Please install it:\npip install Pillow")
        except Exception as e:
            self.show_error(f"Processing failed: {e}")
    
    def show_error(self, message):
        """Show error dialog"""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Error"
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()
    
    def show_info(self, message):
        """Show info dialog"""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Success"
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()


def main():
    app = TShirtMockupApp()
    app.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
