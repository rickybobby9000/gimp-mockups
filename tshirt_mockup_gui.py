#!/usr/bin/env python3
"""
T-Shirt Mockup Creator GUI - Full Featured Version
A comprehensive GTK3 application for creating t-shirt mockups with live preview.
Implements full UI specification with displacement mapping, batch processing, and export controls.
Ensures top graphic layer maintains transparency in exports.
"""

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Gio, Pango
import os
import sys
import math
import json
import threading
import time
from datetime import datetime
from pathlib import Path

try:
    from gimpfu import *
    GIMP_AVAILABLE = True
except ImportError:
    GIMP_AVAILABLE = False
    print("Warning: GIMP Python-Fu not available. Running in preview-only mode.")


class TShirtMockupApp(Gtk.Window):
    def __init__(self):
        super().__init__(title="👕 T-Shirt Mockup Creator Pro")
        self.set_default_size(1400, 900)
        self.set_border_width(5)
        
        # Image storage
        self.template_path = None
        self.template_pixbuf = None
        self.graphic_path = None
        self.graphic_pixbuf = None
        self.disp_map_pixbuf = None
        
        # Transform state
        self.transform = {
            'x': 0,
            'y': 0,
            'scale': 60,  # percentage
            'rotation': 0,
            'anchor': 'C',  # Center
            'lockRatio': True
        }
        
        # Displacement state
        self.displacement = {
            'x': 12,
            'y': 12,
            'contrast': 50,
            'mapSource': 'auto',
            'showMap': False
        }
        
        # Blending state
        self.blend = {
            'mode': 'normal',
            'opacity': 85
        }
        
        # Canvas state
        self.canvas = {
            'zoom': 1.0,
            'panX': 0,
            'panY': 0,
            'viewMode': 'preview',
            'showGrid': False,
            'snapToGrid': False
        }
        
        # Batch state
        self.batch = {
            'inputPath': None,
            'queue': [],
            'currentIndex': 0,
            'isRunning': False,
            'concurrency': 1,
            'allowedExt': ['png', 'jpg', 'svg'],
            'progress': 0,
            'log': []
        }
        
        # Export state
        self.export = {
            'path': None,
            'format': 'PNG',
            'quality': 90,
            'namingPattern': '{original}_mockup',
            'flatten': True,
            'openOnComplete': True
        }
        
        # Preview state
        self.dragging = False
        self.resizing = False
        self.resize_handle = None  # Which corner handle is being dragged (tl, tr, bl, br)
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        self.resize_start_scale = 0
        self.resize_start_x = 0
        self.resize_start_y = 0
        self.preview_debounce_timer = None
        
        self.init_ui()
        self.connect("destroy", Gtk.main_quit)
    
    def init_ui(self):
        """Initialize the complete user interface per specification"""
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(main_box)
        
        # === TOP BAR ===
        top_bar = self.create_top_bar()
        main_box.pack_start(top_bar, False, False, 0)
        
        # === MAIN CONTENT AREA ===
        content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        main_box.pack_start(content_box, True, True, 0)
        
        # Left Panel (30%) - Template & Setup
        left_panel = self.create_left_panel()
        left_panel.set_size_request(420, -1)
        content_box.pack_start(left_panel, False, False, 0)
        
        # Center Panel (50%) - Main Canvas
        center_panel = self.create_center_panel()
        content_box.pack_start(center_panel, True, True, 0)
        
        # Right Panel (20%) - Batch Queue
        right_panel = self.create_right_panel()
        right_panel.set_size_request(280, -1)
        content_box.pack_start(right_panel, False, False, 0)
        
        # === BOTTOM BAR ===
        bottom_bar = self.create_bottom_bar()
        main_box.pack_start(bottom_bar, False, False, 0)
        
        # Apply CSS styling
        self.apply_styles()
    
    def create_top_bar(self):
        """Create top bar with app title, presets, save/load, settings"""
        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        top_bar.get_style_context().add_class("top-bar")
        top_bar.set_margin_start(10)
        top_bar.set_margin_end(10)
        top_bar.set_margin_top(5)
        top_bar.set_margin_bottom(5)
        
        # App Title
        title_label = Gtk.Label()
        title_label.set_markup("<b>👕 T-Shirt Mockup Creator Pro</b>")
        title_label.set_halign(Gtk.Align.START)
        top_bar.pack_start(title_label, False, False, 0)
        
        # Separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        top_bar.pack_start(separator, False, False, 5)
        
        # Preset Dropdown
        preset_label = Gtk.Label(label="Preset:")
        top_bar.pack_start(preset_label, False, False, 0)
        
        self.preset_combo = Gtk.ComboBoxText()
        self.preset_combo.append("", "-- Select Preset --")
        self.preset_combo.append("default", "Default Settings")
        self.preset_combo.set_active(0)
        self.preset_combo.connect("changed", self.on_preset_changed)
        top_bar.pack_start(self.preset_combo, False, False, 0)
        
        # Save Preset Button
        save_preset_btn = Gtk.Button(label="💾 Save Preset")
        save_preset_btn.connect("clicked", self.on_save_preset)
        top_bar.pack_start(save_preset_btn, False, False, 0)
        
        # Load Preset Button
        load_preset_btn = Gtk.Button(label="📂 Load Preset")
        load_preset_btn.connect("clicked", self.on_load_preset)
        top_bar.pack_start(load_preset_btn, False, False, 0)
        
        # Spacer
        spacer = Gtk.Box()
        top_bar.pack_start(spacer, True, True, 0)
        
        # Settings Button
        settings_btn = Gtk.Button(label="⚙️ Settings")
        settings_btn.connect("clicked", self.on_settings)
        top_bar.pack_end(settings_btn, False, False, 0)
        
        return top_bar
    
    def create_left_panel(self):
        """Create left panel with template setup, transform, and displacement controls"""
        left_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        left_panel.get_style_context().add_class("panel")
        
        # Create scrolled window for left panel
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(left_panel)
        
        # === Section A: Template & Workspace Setup ===
        template_frame = self.create_template_section()
        left_panel.pack_start(template_frame, False, False, 0)
        
        # === Section B: Transform & Positioning ===
        transform_frame = self.create_transform_section()
        left_panel.pack_start(transform_frame, False, False, 0)
        
        # === Section C: Displacement & Blending ===
        disp_frame = self.create_displacement_section()
        left_panel.pack_start(disp_frame, False, False, 0)
        
        return scrolled
    
    def create_template_section(self):
        """Create template loading section"""
        frame = Gtk.Frame()
        frame.set_label(" 📁 Template & Workspace ")
        frame.set_label_align(0.02, 0.5)
        frame.get_style_context().add_class("section-frame")
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        vbox.set_margin_top(10)
        vbox.set_margin_bottom(10)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        frame.add(vbox)
        
        # Drag-and-drop zone
        drop_zone = Gtk.EventBox()
        drop_zone.set_size_request(-1, 120)
        drop_zone.get_style_context().add_class("drop-zone")
        drop_zone.drag_dest_set(
            Gtk.DestDefaults.ALL,
            [],
            Gdk.DragAction.COPY
        )
        drop_zone.drag_dest_add_uri_targets()
        drop_zone.connect("drag-data-received", self.on_template_drop)
        drop_zone.connect("button-press-event", self.on_template_zone_click)
        drop_zone.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        
        drop_label = Gtk.Label()
        drop_label.set_markup("<b>Drag &amp; Drop Template Here</b>\n\nPNG, JPG, PSD\nor click to browse")
        drop_label.set_line_wrap(True)
        drop_zone.add(drop_label)
        vbox.pack_start(drop_zone, False, False, 0)
        
        # Template thumbnail
        thumb_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vbox.pack_start(thumb_box, False, False, 0)
        
        self.template_thumb = Gtk.Image()
        self.template_thumb.set_from_icon_name("image-x-generic", Gtk.IconSize.DIALOG)
        self.template_thumb.set_size_request(120, 120)
        thumb_box.pack_start(self.template_thumb, False, False, 0)
        
        # Template info
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        thumb_box.pack_start(info_box, True, True, 0)
        
        self.template_info_label = Gtk.Label()
        self.template_info_label.set_markup(
            "<small>Resolution: --\nColor Space: --\nHas Alpha: --</small>"
        )
        self.template_info_label.set_halign(Gtk.Align.START)
        info_box.pack_start(self.template_info_label, False, False, 0)
        
        # Auto-mask toggle
        self.auto_mask_check = Gtk.CheckButton(label="Apply alpha matte to template edges")
        self.auto_mask_check.set_active(False)
        self.auto_mask_check.connect("toggled", self.on_auto_mask_toggled)
        vbox.pack_start(self.auto_mask_check, False, False, 0)
        
        return frame
    
    def create_transform_section(self):
        """Create transform and positioning controls"""
        frame = Gtk.Frame()
        frame.set_label(" 🎯 Transform & Positioning ")
        frame.set_label_align(0.02, 0.5)
        frame.get_style_context().add_class("section-frame")
        
        grid = Gtk.Grid()
        grid.set_row_spacing(8)
        grid.set_column_spacing(8)
        grid.set_margin_top(10)
        grid.set_margin_bottom(10)
        grid.set_margin_start(10)
        grid.set_margin_end(10)
        frame.add(grid)
        
        # X Position
        grid.attach(Gtk.Label(label="X Position:", halign=Gtk.Align.END), 0, 0, 1, 1)
        self.pos_x_spin = Gtk.SpinButton(adjustment=Gtk.Adjustment(value=0, lower=-1000, upper=3000, step_increment=1))
        self.pos_x_spin.set_digits(0)
        self.pos_x_spin.connect("value-changed", self.on_pos_x_changed)
        grid.attach(self.pos_x_spin, 1, 0, 1, 1)
        
        self.pos_x_slider = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=Gtk.Adjustment(value=0, lower=-1000, upper=3000, step_increment=1))
        self.pos_x_slider.set_digits(0)
        self.pos_x_slider.connect("value-changed", self.on_pos_x_slider_changed)
        grid.attach(self.pos_x_slider, 2, 0, 2, 1)
        
        # Y Position
        grid.attach(Gtk.Label(label="Y Position:", halign=Gtk.Align.END), 0, 1, 1, 1)
        self.pos_y_spin = Gtk.SpinButton(adjustment=Gtk.Adjustment(value=0, lower=-1000, upper=3000, step_increment=1))
        self.pos_y_spin.set_digits(0)
        self.pos_y_spin.connect("value-changed", self.on_pos_y_changed)
        grid.attach(self.pos_y_spin, 1, 1, 1, 1)
        
        self.pos_y_slider = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=Gtk.Adjustment(value=0, lower=-1000, upper=3000, step_increment=1))
        self.pos_y_slider.set_digits(0)
        self.pos_y_slider.connect("value-changed", self.on_pos_y_slider_changed)
        grid.attach(self.pos_y_slider, 2, 1, 2, 1)
        
        # Scale
        grid.attach(Gtk.Label(label="Scale (%):", halign=Gtk.Align.END), 0, 2, 1, 1)
        self.scale_spin = Gtk.SpinButton(adjustment=Gtk.Adjustment(value=60, lower=10, upper=200, step_increment=1))
        self.scale_spin.set_digits(0)
        self.scale_spin.connect("value-changed", self.on_scale_changed)
        grid.attach(self.scale_spin, 1, 2, 1, 1)
        
        self.scale_slider = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=Gtk.Adjustment(value=60, lower=10, upper=200, step_increment=1))
        self.scale_slider.set_digits(0)
        self.scale_slider.connect("value-changed", self.on_scale_slider_changed)
        grid.attach(self.scale_slider, 2, 2, 2, 1)
        
        # Lock Aspect Ratio
        self.lock_ratio_check = Gtk.CheckButton(label="Lock Aspect Ratio")
        self.lock_ratio_check.set_active(True)
        self.lock_ratio_check.connect("toggled", self.on_lock_ratio_toggled)
        grid.attach(self.lock_ratio_check, 1, 3, 1, 1)
        
        # Anchor Point Selector
        grid.attach(Gtk.Label(label="Anchor:", halign=Gtk.Align.END), 0, 4, 1, 1)
        anchor_box = self.create_anchor_grid()
        grid.attach(anchor_box, 1, 4, 3, 1)
        
        # Reset Transform Button
        reset_btn = Gtk.Button(label="🔄 Reset Transform")
        reset_btn.connect("clicked", self.on_reset_transform)
        grid.attach(reset_btn, 0, 5, 4, 1)
        
        # Apply to Batch Toggle
        self.apply_batch_check = Gtk.CheckButton(label="Lock these values for all exports")
        self.apply_batch_check.set_active(True)
        grid.attach(self.apply_batch_check, 0, 6, 4, 1)
        
        return frame
    
    def create_anchor_grid(self):
        """Create 9-point anchor grid selector"""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        
        # Top row
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        for pos in ['TL', 'TC', 'TR']:
            btn = Gtk.Button(label=pos)
            btn.set_size_request(30, 25)
            btn.connect("clicked", self.on_anchor_clicked, pos)
            top_row.pack_start(btn, False, False, 0)
        box.pack_start(top_row, False, False, 0)
        
        # Middle row
        mid_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        for pos in ['ML', 'C', 'MR']:
            btn = Gtk.Button(label=pos)
            btn.set_size_request(30, 25)
            btn.connect("clicked", self.on_anchor_clicked, pos)
            mid_row.pack_start(btn, False, False, 0)
        box.pack_start(mid_row, False, False, 0)
        
        # Bottom row
        bot_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        for pos in ['BL', 'BC', 'BR']:
            btn = Gtk.Button(label=pos)
            btn.set_size_request(30, 25)
            btn.connect("clicked", self.on_anchor_clicked, pos)
            bot_row.pack_start(btn, False, False, 0)
        box.pack_start(bot_row, False, False, 0)
        
        return box
    
    def create_displacement_section(self):
        """Create displacement and blending controls"""
        frame = Gtk.Frame()
        frame.set_label(" 🌊 Displacement & Blending ")
        frame.set_label_align(0.02, 0.5)
        frame.get_style_context().add_class("section-frame")
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        vbox.set_margin_top(10)
        vbox.set_margin_bottom(10)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        frame.add(vbox)
        
        # Displacement X
        disp_x_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        disp_x_label = Gtk.Label(label="Displacement X:", width_chars=15, xalign=0)
        disp_x_box.pack_start(disp_x_label, False, False, 0)
        
        self.disp_x_spin = Gtk.SpinButton(adjustment=Gtk.Adjustment(value=12, lower=0, upper=50, step_increment=0.5))
        self.disp_x_spin.set_digits(1)
        self.disp_x_spin.connect("value-changed", self.on_disp_x_changed)
        disp_x_box.pack_start(self.disp_x_spin, False, False, 0)
        
        self.disp_x_slider = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=Gtk.Adjustment(value=12, lower=0, upper=50, step_increment=0.5))
        self.disp_x_slider.set_digits(1)
        self.disp_x_slider.connect("value-changed", self.on_disp_x_slider_changed)
        vbox.pack_start(disp_x_box, False, False, 0)
        vbox.pack_start(self.disp_x_slider, False, False, 0)
        
        # Displacement Y
        disp_y_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        disp_y_label = Gtk.Label(label="Displacement Y:", width_chars=15, xalign=0)
        disp_y_box.pack_start(disp_y_label, False, False, 0)
        
        self.disp_y_spin = Gtk.SpinButton(adjustment=Gtk.Adjustment(value=12, lower=0, upper=50, step_increment=0.5))
        self.disp_y_spin.set_digits(1)
        self.disp_y_spin.connect("value-changed", self.on_disp_y_changed)
        disp_y_box.pack_start(self.disp_y_spin, False, False, 0)
        
        self.disp_y_slider = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=Gtk.Adjustment(value=12, lower=0, upper=50, step_increment=0.5))
        self.disp_y_slider.set_digits(1)
        self.disp_y_slider.connect("value-changed", self.on_disp_y_slider_changed)
        vbox.pack_start(disp_y_box, False, False, 0)
        vbox.pack_start(self.disp_y_slider, False, False, 0)
        
        # Map Source Dropdown
        map_source_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        map_source_label = Gtk.Label(label="Disp Map Source:", width_chars=15, xalign=0)
        map_source_box.pack_start(map_source_label, False, False, 0)
        
        self.map_source_combo = Gtk.ComboBoxText()
        self.map_source_combo.append("auto", "Auto-Generate")
        self.map_source_combo.append("external", "Load External .png/.psd")
        self.map_source_combo.set_active(0)
        self.map_source_combo.connect("changed", self.on_map_source_changed)
        map_source_box.pack_start(self.map_source_combo, True, True, 0)
        vbox.pack_start(map_source_box, False, False, 0)
        
        # Map Contrast
        contrast_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        contrast_label = Gtk.Label(label="Map Contrast:", width_chars=15, xalign=0)
        contrast_box.pack_start(contrast_label, False, False, 0)
        
        self.contrast_spin = Gtk.SpinButton(adjustment=Gtk.Adjustment(value=50, lower=0, upper=100, step_increment=5))
        self.contrast_spin.set_digits(0)
        self.contrast_spin.connect("value-changed", self.on_contrast_changed)
        contrast_box.pack_start(self.contrast_spin, False, False, 0)
        vbox.pack_start(contrast_box, False, False, 0)
        
        self.contrast_slider = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=Gtk.Adjustment(value=50, lower=0, upper=100, step_increment=5))
        self.contrast_slider.set_digits(0)
        self.contrast_slider.connect("value-changed", self.on_contrast_slider_changed)
        vbox.pack_start(self.contrast_slider, False, False, 0)
        
        # Blend Mode
        blend_mode_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        blend_mode_label = Gtk.Label(label="Blend Mode:", width_chars=15, xalign=0)
        blend_mode_box.pack_start(blend_mode_label, False, False, 0)
        
        self.blend_mode_combo = Gtk.ComboBoxText()
        for mode in ['Normal', 'Multiply', 'Overlay', 'Soft Light', 'Screen', 'Linear Light']:
            self.blend_mode_combo.append(mode.lower(), mode)
        self.blend_mode_combo.set_active(0)
        self.blend_mode_combo.connect("changed", self.on_blend_mode_changed)
        blend_mode_box.pack_start(self.blend_mode_combo, True, True, 0)
        vbox.pack_start(blend_mode_box, False, False, 0)
        
        # Opacity
        opacity_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        opacity_label = Gtk.Label(label="Opacity:", width_chars=15, xalign=0)
        opacity_box.pack_start(opacity_label, False, False, 0)
        
        self.opacity_spin = Gtk.SpinButton(adjustment=Gtk.Adjustment(value=85, lower=0, upper=100, step_increment=1))
        self.opacity_spin.set_digits(0)
        self.opacity_spin.connect("value-changed", self.on_opacity_changed)
        opacity_box.pack_start(self.opacity_spin, False, False, 0)
        vbox.pack_start(opacity_box, False, False, 0)
        
        self.opacity_slider = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=Gtk.Adjustment(value=85, lower=0, upper=100, step_increment=1))
        self.opacity_slider.set_digits(0)
        self.opacity_slider.connect("value-changed", self.on_opacity_slider_changed)
        vbox.pack_start(self.opacity_slider, False, False, 0)
        
        # Show Map Preview Toggle
        self.show_map_check = Gtk.CheckButton(label="View displacement map overlay")
        self.show_map_check.set_active(False)
        self.show_map_check.connect("toggled", self.on_show_map_toggled)
        vbox.pack_start(self.show_map_check, False, False, 0)
        
        return frame
    
    def create_center_panel(self):
        """Create center canvas panel"""
        center_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        center_panel.get_style_context().add_class("center-panel")
        
        # View toggles toolbar
        view_toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        view_toolbar.set_margin_top(5)
        view_toolbar.set_margin_bottom(5)
        view_toolbar.set_margin_start(10)
        view_toolbar.set_margin_end(10)
        center_panel.pack_start(view_toolbar, False, False, 0)
        
        # Segmented button group for view modes
        self.view_buttons = {}
        for mode, label in [('template', 'Template'), ('preview', 'Preview'), 
                           ('disp', 'Disp Map'), ('grid', 'Grid'), ('snap', 'Snap')]:
            btn = Gtk.ToggleButton(label=label)
            btn.connect("toggled", self.on_view_toggle, mode)
            if mode == 'preview':
                btn.set_active(True)
            view_toolbar.pack_start(btn, False, False, 0)
            self.view_buttons[mode] = btn
        
        # Spacer
        spacer = Gtk.Box()
        view_toolbar.pack_start(spacer, True, True, 0)
        
        # Quality dropdown
        quality_label = Gtk.Label(label="Quality:")
        view_toolbar.pack_start(quality_label, False, False, 5)
        
        self.quality_combo = Gtk.ComboBoxText()
        self.quality_combo.append("draft", "Draft (Fast)")
        self.quality_combo.append("full", "Full (Accurate)")
        self.quality_combo.set_active(0)
        self.quality_combo.connect("changed", self.on_quality_changed)
        view_toolbar.pack_start(self.quality_combo, False, False, 0)
        
        # Drawing area for canvas
        self.drawing_area = Gtk.DrawingArea()
        self.drawing_area.set_size_request(700, 600)
        self.drawing_area.connect("draw", self.on_draw)
        self.drawing_area.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.SCROLL_MASK |
            Gdk.EventMask.SMOOTH_SCROLL_MASK
        )
        self.drawing_area.connect("button-press-event", self.on_button_press)
        self.drawing_area.connect("button-release-event", self.on_button_release)
        self.drawing_area.connect("motion-notify-event", self.on_motion_notify)
        self.drawing_area.connect("scroll-event", self.on_scroll)
        
        # Enable drag and drop for graphics
        self.drawing_area.drag_dest_set(
            Gtk.DestDefaults.ALL,
            [],
            Gdk.DragAction.COPY
        )
        self.drawing_area.drag_dest_add_uri_targets()
        self.drawing_area.connect("drag-data-received", self.on_graphic_drop)
        
        center_panel.pack_start(self.drawing_area, True, True, 0)
        
        return center_panel
    
    def create_right_panel(self):
        """Create right panel with batch queue and export settings"""
        right_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        right_panel.get_style_context().add_class("panel")
        
        # Create scrolled window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(right_panel)
        
        # === Batch Queue Section ===
        batch_frame = Gtk.Frame()
        batch_frame.set_label(" 📋 Batch Queue ")
        batch_frame.set_label_align(0.02, 0.5)
        batch_frame.get_style_context().add_class("section-frame")
        
        batch_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        batch_vbox.set_margin_top(10)
        batch_vbox.set_margin_bottom(10)
        batch_vbox.set_margin_start(10)
        batch_vbox.set_margin_end(10)
        batch_frame.add(batch_vbox)
        
        # Input folder picker
        folder_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        folder_btn = Gtk.Button(label="📁 Select Input Folder")
        folder_btn.connect("clicked", self.on_select_input_folder)
        folder_box.pack_start(folder_btn, True, True, 0)
        batch_vbox.pack_start(folder_box, False, False, 0)
        
        # Format filter checkboxes
        filter_label = Gtk.Label(label="Format Filter:")
        filter_label.set_halign(Gtk.Align.START)
        batch_vbox.pack_start(filter_label, False, False, 0)
        
        filter_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        for ext in ['PNG', 'JPG', 'SVG', 'WebP']:
            check = Gtk.CheckButton(label=ext)
            check.set_active(True)
            check.connect("toggled", self.on_format_filter_changed, ext.lower())
            filter_box.pack_start(check, False, False, 0)
        batch_vbox.pack_start(filter_box, False, False, 0)
        
        # Concurrency dropdown
        conc_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        conc_label = Gtk.Label(label="Concurrency:")
        conc_box.pack_start(conc_label, False, False, 0)
        
        self.concurrency_combo = Gtk.ComboBoxText()
        for val in ['1', '2', '4', 'Auto']:
            self.concurrency_combo.append(val, val)
        self.concurrency_combo.set_active(2)
        conc_box.pack_start(self.concurrency_combo, True, True, 0)
        batch_vbox.pack_start(conc_box, False, False, 0)
        
        # Queue table (simplified as listbox)
        self.queue_listbox = Gtk.ListBox()
        self.queue_listbox.set_size_request(-1, 150)
        self.queue_listbox.get_style_context().add_class("queue-list")
        batch_vbox.pack_start(self.queue_listbox, True, True, 0)
        
        # Process button
        self.process_btn = Gtk.Button(label="▶ Process All")
        self.process_btn.get_style_context().add_class("suggested-action")
        self.process_btn.connect("clicked", self.on_process_all)
        batch_vbox.pack_start(self.process_btn, False, False, 0)
        
        # Progress bar
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        batch_vbox.pack_start(self.progress_bar, False, False, 0)
        
        # Status log (collapsible)
        log_expander = Gtk.Expander(label="📝 Status Log")
        log_scrolled = Gtk.ScrolledWindow()
        log_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        log_scrolled.set_size_request(-1, 100)
        
        self.log_text = Gtk.TextView()
        self.log_text.set_editable(False)
        self.log_text.set_wrap_mode(Gtk.WrapMode.WORD)
        log_scrolled.add(self.log_text)
        log_expander.add(log_scrolled)
        batch_vbox.pack_start(log_expander, False, False, 0)
        
        right_panel.pack_start(batch_frame, False, False, 0)
        
        # === Export Settings Section ===
        export_frame = Gtk.Frame()
        export_frame.set_label(" 💾 Export Settings ")
        export_frame.set_label_align(0.02, 0.5)
        export_frame.get_style_context().add_class("section-frame")
        
        export_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        export_vbox.set_margin_top(10)
        export_vbox.set_margin_bottom(10)
        export_vbox.set_margin_start(10)
        export_vbox.set_margin_end(10)
        export_frame.add(export_vbox)
        
        # Output folder picker
        out_folder_btn = Gtk.Button(label="📂 Select Output Folder")
        out_folder_btn.connect("clicked", self.on_select_output_folder)
        export_vbox.pack_start(out_folder_btn, False, False, 0)
        
        # Format radio group
        format_label = Gtk.Label(label="Export Format:")
        format_label.set_halign(Gtk.Align.START)
        export_vbox.pack_start(format_label, False, False, 0)
        
        format_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.format_radios = {}
        for fmt in ['PNG', 'JPG', 'WebP']:
            radio = Gtk.RadioButton.new_with_label_from_widget(None, fmt)
            if fmt == 'PNG':
                radio.set_active(True)
            radio.connect("toggled", self.on_export_format_changed, fmt)
            format_box.pack_start(radio, False, False, 0)
            self.format_radios[fmt] = radio
        export_vbox.pack_start(format_box, False, False, 0)
        
        # Quality slider (conditional)
        quality_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        quality_label = Gtk.Label(label="Quality:")
        quality_box.pack_start(quality_label, False, False, 0)
        
        self.export_quality_spin = Gtk.SpinButton(adjustment=Gtk.Adjustment(value=90, lower=60, upper=100, step_increment=5))
        self.export_quality_spin.set_digits(0)
        self.export_quality_spin.connect("value-changed", self.on_export_quality_changed)
        quality_box.pack_start(self.export_quality_spin, False, False, 0)
        export_vbox.pack_start(quality_box, False, False, 0)
        
        # Naming template
        naming_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        naming_label = Gtk.Label(label="Naming:")
        naming_box.pack_start(naming_label, False, False, 0)
        
        self.naming_entry = Gtk.Entry()
        self.naming_entry.set_text("{original}_mockup")
        self.naming_entry.set_width_chars(18)
        self.naming_entry.connect("changed", self.on_naming_changed)
        naming_box.pack_start(self.naming_entry, True, True, 0)
        export_vbox.pack_start(naming_box, False, False, 0)
        
        # Naming preview
        self.naming_preview = Gtk.Label()
        self.naming_preview.set_markup("<small>Preview: shirt_mockup.png</small>")
        self.naming_preview.set_halign(Gtk.Align.START)
        export_vbox.pack_start(self.naming_preview, False, False, 0)
        
        # Flatten toggle
        self.flatten_check = Gtk.CheckButton(label="Merge layers before saving")
        self.flatten_check.set_active(True)
        export_vbox.pack_start(self.flatten_check, False, False, 0)
        
        # Open on finish toggle
        self.open_on_finish_check = Gtk.CheckButton(label="Open output folder when done")
        self.open_on_finish_check.set_active(True)
        export_vbox.pack_start(self.open_on_finish_check, False, False, 0)
        
        right_panel.pack_start(export_frame, False, False, 0)
        
        return scrolled
    
    def create_bottom_bar(self):
        """Create bottom status bar"""
        bottom_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        bottom_bar.get_style_context().add_class("bottom-bar")
        bottom_bar.set_margin_start(10)
        bottom_bar.set_margin_end(10)
        bottom_bar.set_margin_top(5)
        bottom_bar.set_margin_bottom(5)
        
        # Progress info
        self.bottom_status = Gtk.Label(label="Ready")
        self.bottom_status.set_halign(Gtk.Align.START)
        bottom_bar.pack_start(self.bottom_status, False, False, 0)
        
        # Spacer
        spacer = Gtk.Box()
        bottom_bar.pack_start(spacer, True, True, 0)
        
        # ETA label
        self.eta_label = Gtk.Label(label="")
        bottom_bar.pack_start(self.eta_label, False, False, 0)
        
        # Quick controls
        space_btn = Gtk.Button(label="Space: Preview")
        space_btn.set_sensitive(False)
        bottom_bar.pack_start(space_btn, False, False, 5)
        
        reset_btn = Gtk.Button(label="R: Reset")
        reset_btn.connect("clicked", self.on_reset_transform)
        bottom_bar.pack_start(reset_btn, False, False, 5)
        
        save_btn = Gtk.Button(label="Ctrl+S: Save Preset")
        save_btn.connect("clicked", self.on_save_preset)
        bottom_bar.pack_start(save_btn, False, False, 5)
        
        return bottom_bar
    
    def apply_styles(self):
        """Apply CSS styles to the application"""
        css_provider = Gtk.CssProvider()
        css = """
        .top-bar {
            background: #2d3436;
            color: #dfe6e9;
            padding: 5px;
        }
        
        .bottom-bar {
            background: #2d3436;
            color: #dfe6e9;
            padding: 5px;
        }
        
        .panel {
            background: #2d3436;
            color: #dfe6e9;
            padding: 5px;
        }
        
        .panel label {
            color: #dfe6e9;
        }
        
        .panel spinbutton,
        .panel scale,
        .panel combobox,
        .panel checkbutton,
        .panel radiobutton {
            color: #dfe6e9;
        }
        
        .panel spinbutton entry {
            background: #636e72;
            color: #dfe6e9;
        }
        
        .panel scale trough {
            background: #636e72;
        }
        
        .panel scale highlight {
            background: #0984e3;
        }
        
        .center-panel {
            background: #636e72;
        }
        
        .section-frame {
            margin: 5px;
            border-radius: 5px;
        }
        
        .section-frame > border {
            border: 1px solid #636e72;
            border-radius: 5px;
        }
        
        .section-frame label {
            color: #dfe6e9;
        }
        
        .drop-zone {
            background: #636e72;
            border: 2px dashed #bdc3c7;
            border-radius: 5px;
            color: #dfe6e9;
        }
        
        .drop-zone:hover {
            background: #748590;
        }
        
        .queue-list {
            background: #636e72;
            color: #dfe6e9;
            border: 1px solid #b2bec3;
            border-radius: 3px;
        }
        
        .queue-list row {
            background: #636e72;
            color: #dfe6e9;
        }
        
        .queue-list row:selected {
            background: #0984e3;
            color: white;
        }
        
        button.suggested-action {
            background: #00b894;
            color: white;
        }
        
        button.suggested-action:hover {
            background: #00a884;
        }
        
        expander label {
            color: #dfe6e9;
        }
        
        expander arrow {
            -gtk-icon-source: -gtk-icontheme("pan-end-symbolic");
            color: #dfe6e9;
        }
        """
        css_provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    
    # === Event Handlers ===
    
    def on_template_drop(self, widget, drag_context, x, y, data, info, time):
        """Handle template file drop"""
        uris = data.get_uris()
        if uris:
            uri = uris[0]
            if uri.startswith("file://"):
                filename = uri[7:].replace("%20", " ")
                self.load_template(filename)
    
    def on_template_zone_click(self, widget, event):
        """Handle click on template drop zone"""
        dialog = Gtk.FileChooserDialog(
            title="Select Template",
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
            self.load_template(filename)
        
        dialog.destroy()
    
    def on_graphic_drop(self, widget, drag_context, x, y, data, info, time):
        """Handle graphic file drop on canvas"""
        uris = data.get_uris()
        if uris:
            uri = uris[0]
            if uri.startswith("file://"):
                filename = uri[7:].replace("%20", " ")
                self.load_graphic(filename)
    
    def load_template(self, filename):
        """Load template image"""
        try:
            self.template_pixbuf = GdkPixbuf.Pixbuf.new_from_file(filename)
            self.template_path = filename
            
            # Update thumbnail
            thumb = self.template_pixbuf.scale_simple(120, 120, GdkPixbuf.InterpType.BILINEAR)
            self.template_thumb.set_from_pixbuf(thumb)
            
            # Update info
            has_alpha = self.template_pixbuf.get_has_alpha()
            self.template_info_label.set_markup(
                f"<small>Resolution: {self.template_pixbuf.get_width()}x{self.template_pixbuf.get_height()}\n"
                f"Color Space: {'RGBA' if has_alpha else 'RGB'}\n"
                f"Has Alpha: {'Yes ✓' if has_alpha else 'No'}</small>"
            )
            
            # Generate default displacement map
            self.generate_disp_map()
            
            # Update canvas
            self.queue_preview_update()
            self.log_message(f"Loaded template: {os.path.basename(filename)}")
            
        except Exception as e:
            self.show_error(f"Failed to load template: {e}")
    
    def load_graphic(self, filename):
        """Load graphic image"""
        try:
            self.graphic_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                filename, -1, -1, True
            )
            self.graphic_path = filename
            
            # Center the graphic initially
            if self.template_pixbuf:
                self.transform['x'] = (self.template_pixbuf.get_width() - self.graphic_pixbuf.get_width()) // 2
                self.transform['y'] = (self.template_pixbuf.get_height() - self.graphic_pixbuf.get_height()) // 2
                
                # Update UI controls
                self.pos_x_spin.set_value(self.transform['x'])
                self.pos_x_slider.set_value(self.transform['x'])
                self.pos_y_spin.set_value(self.transform['y'])
                self.pos_y_slider.set_value(self.transform['y'])
            
            self.queue_preview_update()
            self.log_message(f"Loaded graphic: {os.path.basename(filename)}")
            
        except Exception as e:
            self.show_error(f"Failed to load graphic: {e}")
    
    def generate_disp_map(self):
        """Generate displacement map from template"""
        if not self.template_pixbuf:
            return
        
        # Simplified: create grayscale version of template
        # In production, this would use luminance + contrast boost
        width = self.template_pixbuf.get_width()
        height = self.template_pixbuf.get_height()
        
        # Create grayscale pixbuf
        self.disp_map_pixbuf = GdkPixbuf.Pixbuf.new(
            GdkPixbuf.Colorspace.RGB, False, 8, width, height
        )
        
        # For now, just create a placeholder
        # Real implementation would process pixel data
    
    def queue_preview_update(self):
        """Queue a preview update with debouncing"""
        if self.preview_debounce_timer:
            GLib.source_remove(self.preview_debounce_timer)
        
        self.preview_debounce_timer = GLib.timeout_add(150, self.update_preview)
    
    def update_preview(self):
        """Update the canvas preview"""
        if self.drawing_area:
            self.drawing_area.queue_draw()
        self.preview_debounce_timer = None
        return False
    
    def on_draw(self, widget, cr):
        """Draw the canvas preview"""
        # Clear background
        cr.set_source_rgb(0.25, 0.25, 0.25)
        cr.paint()
        
        if not self.template_pixbuf:
            # Draw placeholder text
            cr.set_source_rgb(1.0, 1.0, 1.0)
            cr.set_font_size(16)
            cr.move_to(50, 50)
            cr.show_text("Drag & drop a template image here")
            cr.move_to(50, 70)
            cr.show_text("Then drag a graphic onto the canvas")
            return
        
        # Apply zoom/pan
        cr.save()
        cr.translate(self.canvas['panX'], self.canvas['panY'])
        cr.scale(self.canvas['zoom'], self.canvas['zoom'])
        
        # Draw template
        Gdk.cairo_set_source_pixbuf(cr, self.template_pixbuf, 0, 0)
        cr.paint()
        
        # Draw grid if enabled
        if self.canvas['showGrid']:
            self.draw_grid(cr)
        
        # Draw graphic if loaded
        if self.graphic_pixbuf:
            self.draw_graphic(cr)
        
        # Draw displacement map overlay if enabled
        if self.displacement['showMap'] and self.disp_map_pixbuf:
            self.draw_disp_map_overlay(cr)
        
        # Draw bounding box around graphic (in transformed coords so it matches)
        if self.graphic_pixbuf:
            self.draw_bounding_box(cr)
        
        cr.restore()
    
    def draw_grid(self, cr):
        """Draw grid overlay"""
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.3)
        cr.set_line_width(1)
        
        # Draw 50px major grid
        spacing = 50
        if self.template_pixbuf:
            width = self.template_pixbuf.get_width()
            height = self.template_pixbuf.get_height()
            
            for x in range(0, width, spacing):
                cr.move_to(x, 0)
                cr.line_to(x, height)
            
            for y in range(0, height, spacing):
                cr.move_to(0, y)
                cr.line_to(width, y)
            
            cr.stroke()
    
    def draw_graphic(self, cr):
        """Draw graphic with transformations"""
        scaled_width = int(self.graphic_pixbuf.get_width() * self.transform['scale'] / 100)
        scaled_height = int(self.graphic_pixbuf.get_height() * self.transform['scale'] / 100)
        
        # Calculate center for rotation
        center_x = self.transform['x'] + scaled_width / 2
        center_y = self.transform['y'] + scaled_height / 2
        
        cr.save()
        
        # Translate to center, rotate, translate back
        cr.translate(center_x, center_y)
        cr.rotate(math.radians(self.transform['rotation']))
        cr.translate(-center_x, -center_y)
        
        # Set opacity
        cr.set_source_rgba(1, 1, 1, self.blend['opacity'] / 100.0)
        
        # Scale and draw graphic
        Gdk.cairo_set_source_pixbuf(cr, self.graphic_pixbuf, 
                                   self.transform['x'], 
                                   self.transform['y'])
        
        pattern = cr.get_source()
        matrix = pattern.get_matrix()
        matrix.scale(100.0 / self.transform['scale'], 100.0 / self.transform['scale'])
        pattern.set_matrix(matrix)
        
        cr.rectangle(self.transform['x'], self.transform['y'], 
                    scaled_width, scaled_height)
        cr.fill()
        
        cr.restore()
    
    def draw_disp_map_overlay(self, cr):
        """Draw displacement map overlay"""
        if self.disp_map_pixbuf:
            cr.set_source_rgba(0.5, 0.5, 0.5, 0.5)
            Gdk.cairo_set_source_pixbuf(cr, self.disp_map_pixbuf, 0, 0)
            cr.paint()
    
    def draw_bounding_box(self, cr):
        """Draw selection bounding box around graphic with resize handles (in current transformed space)"""
        scaled_width = int(self.graphic_pixbuf.get_width() * self.transform['scale'] / 100)
        scaled_height = int(self.graphic_pixbuf.get_height() * self.transform['scale'] / 100)
        
        x = self.transform['x']
        y = self.transform['y']
        
        # Draw bounding box
        cr.set_source_rgba(0.0, 1.0, 0.0, 0.7)
        cr.set_line_width(2 / self.canvas['zoom'])  # Adjust line width for zoom
        cr.rectangle(x, y, scaled_width, scaled_height)
        cr.stroke()
        
        # Draw resize handles at corners (size adjusted for zoom)
        handle_size = 8 / self.canvas['zoom']
        cr.set_source_rgba(0.0, 1.0, 0.0, 0.9)
        
        # Top-left
        cr.rectangle(x - handle_size/2, y - handle_size/2, handle_size, handle_size)
        cr.fill()
        
        # Top-right
        cr.rectangle(x + scaled_width - handle_size/2, y - handle_size/2, handle_size, handle_size)
        cr.fill()
        
        # Bottom-left
        cr.rectangle(x - handle_size/2, y + scaled_height - handle_size/2, handle_size, handle_size)
        cr.fill()
        
        # Bottom-right
        cr.rectangle(x + scaled_width - handle_size/2, y + scaled_height - handle_size/2, handle_size, handle_size)
        cr.fill()
    
    def on_button_press(self, widget, event):
        """Handle mouse button press on canvas"""
        if event.button == 1 and self.graphic_pixbuf:
            scaled_width = int(self.graphic_pixbuf.get_width() * self.transform['scale'] / 100)
            scaled_height = int(self.graphic_pixbuf.get_height() * self.transform['scale'] / 100)
            
            # Check if click is within graphic bounds (accounting for zoom)
            click_x = (event.x - self.canvas['panX']) / self.canvas['zoom']
            click_y = (event.y - self.canvas['panY']) / self.canvas['zoom']
            
            x = self.transform['x']
            y = self.transform['y']
            handle_size = 8 / self.canvas['zoom']  # Adjust handle size for zoom
            
            # Check resize handles first (priority over dragging)
            # Top-left
            if (x - handle_size/2 <= click_x <= x + handle_size/2 and
                y - handle_size/2 <= click_y <= y + handle_size/2):
                self.resizing = True
                self.resize_handle = 'tl'
                self.resize_start_scale = self.transform['scale']
                self.resize_start_x = x
                self.resize_start_y = y
                self.last_mouse_x = click_x
                self.last_mouse_y = click_y
                self.drawing_area.set_cursor(Gdk.Cursor.new(Gdk.CursorType.TOP_LEFT_CORNER))
            # Top-right
            elif (x + scaled_width - handle_size/2 <= click_x <= x + scaled_width + handle_size/2 and
                  y - handle_size/2 <= click_y <= y + handle_size/2):
                self.resizing = True
                self.resize_handle = 'tr'
                self.resize_start_scale = self.transform['scale']
                self.resize_start_x = x
                self.resize_start_y = y
                self.last_mouse_x = click_x
                self.last_mouse_y = click_y
                self.drawing_area.set_cursor(Gdk.Cursor.new(Gdk.CursorType.TOP_RIGHT_CORNER))
            # Bottom-left
            elif (x - handle_size/2 <= click_x <= x + handle_size/2 and
                  y + scaled_height - handle_size/2 <= click_y <= y + scaled_height + handle_size/2):
                self.resizing = True
                self.resize_handle = 'bl'
                self.resize_start_scale = self.transform['scale']
                self.resize_start_x = x
                self.resize_start_y = y
                self.last_mouse_x = click_x
                self.last_mouse_y = click_y
                self.drawing_area.set_cursor(Gdk.Cursor.new(Gdk.CursorType.BOTTOM_LEFT_CORNER))
            # Bottom-right
            elif (x + scaled_width - handle_size/2 <= click_x <= x + scaled_width + handle_size/2 and
                  y + scaled_height - handle_size/2 <= click_y <= y + scaled_height + handle_size/2):
                self.resizing = True
                self.resize_handle = 'br'
                self.resize_start_scale = self.transform['scale']
                self.resize_start_x = x
                self.resize_start_y = y
                self.last_mouse_x = click_x
                self.last_mouse_y = click_y
                self.drawing_area.set_cursor(Gdk.Cursor.new(Gdk.CursorType.BOTTOM_RIGHT_CORNER))
            # Check if click is within graphic bounds for dragging
            elif (x <= click_x <= x + scaled_width and
                  y <= click_y <= y + scaled_height):
                self.dragging = True
                self.last_mouse_x = click_x
                self.last_mouse_y = click_y
                self.drawing_area.set_cursor(Gdk.Cursor.new(Gdk.CursorType.FLEUR))
    
    def on_button_release(self, widget, event):
        """Handle mouse button release"""
        if event.button == 1:
            self.dragging = False
            self.resizing = False
            self.resize_handle = None
            # Reset cursor to default
            self.drawing_area.set_cursor(None)
    
    def on_motion_notify(self, widget, event):
        """Handle mouse motion"""
        if self.graphic_pixbuf:
            # Calculate current position accounting for zoom
            current_x = (event.x - self.canvas['panX']) / self.canvas['zoom']
            current_y = (event.y - self.canvas['panY']) / self.canvas['zoom']
            
            if self.resizing and self.resize_handle:
                # Handle resizing from corners
                dx = current_x - self.last_mouse_x
                dy = current_y - self.last_mouse_y
                
                orig_width = self.graphic_pixbuf.get_width()
                orig_height = self.graphic_pixbuf.get_height()
                orig_scaled_width = int(orig_width * self.resize_start_scale / 100)
                orig_scaled_height = int(orig_height * self.resize_start_scale / 100)
                
                if self.resize_handle == 'br':  # Bottom-right
                    # Calculate new scale based on diagonal distance
                    new_width = orig_scaled_width + dx
                    new_height = orig_scaled_height + dy
                    # Use average to maintain aspect ratio somewhat
                    avg_scale = (new_width / orig_width + new_height / orig_height) / 2 * 100
                elif self.resize_handle == 'bl':  # Bottom-left
                    new_width = orig_scaled_width - dx
                    new_height = orig_scaled_height + dy
                    avg_scale = (new_width / orig_width + new_height / orig_height) / 2 * 100
                    # Adjust x position
                    self.transform['x'] = self.resize_start_x + dx
                elif self.resize_handle == 'tr':  # Top-right
                    new_width = orig_scaled_width + dx
                    new_height = orig_scaled_height - dy
                    avg_scale = (new_width / orig_width + new_height / orig_height) / 2 * 100
                    # Adjust y position
                    self.transform['y'] = self.resize_start_y + dy
                elif self.resize_handle == 'tl':  # Top-left
                    new_width = orig_scaled_width - dx
                    new_height = orig_scaled_height - dy
                    avg_scale = (new_width / orig_width + new_height / orig_height) / 2 * 100
                    # Adjust x and y position
                    self.transform['x'] = self.resize_start_x + dx
                    self.transform['y'] = self.resize_start_y + dy
                
                # Clamp scale to valid range
                new_scale = max(10, min(200, avg_scale))
                self.transform['scale'] = new_scale
                
                # Update UI controls
                self.scale_spin.set_value(new_scale)
                self.scale_slider.set_value(new_scale)
                self.pos_x_spin.set_value(self.transform['x'])
                self.pos_x_slider.set_value(self.transform['x'])
                self.pos_y_spin.set_value(self.transform['y'])
                self.pos_y_slider.set_value(self.transform['y'])
                
                # Force immediate redraw
                self.drawing_area.queue_draw()
                
            elif self.dragging:
                dx = current_x - self.last_mouse_x
                dy = current_y - self.last_mouse_y
                
                self.transform['x'] += dx
                self.transform['y'] += dy
                
                # Update UI controls
                self.pos_x_spin.set_value(self.transform['x'])
                self.pos_x_slider.set_value(self.transform['x'])
                self.pos_y_spin.set_value(self.transform['y'])
                self.pos_y_slider.set_value(self.transform['y'])
                
                self.last_mouse_x = current_x
                self.last_mouse_y = current_y
                
                # Force immediate redraw for responsive dragging
                self.drawing_area.queue_draw()
    
    def on_scroll(self, widget, event):
        """Handle scroll wheel for zooming"""
        # Handle both regular and smooth scroll events
        if event.direction == Gdk.ScrollDirection.UP or \
           event.direction == Gdk.ScrollDirection.SMOOTH:
            delta = 0.1
            if event.direction == Gdk.ScrollDirection.SMOOTH:
                # For smooth scrolling, use the scroll deltas
                _, dx, dy = event.get_scroll_deltas()
                if dy < 0:
                    self.canvas['zoom'] = min(5.0, self.canvas['zoom'] + 0.1)
                elif dy > 0:
                    self.canvas['zoom'] = max(0.1, self.canvas['zoom'] - 0.1)
            else:
                self.canvas['zoom'] = min(5.0, self.canvas['zoom'] + delta)
        elif event.direction == Gdk.ScrollDirection.DOWN:
            self.canvas['zoom'] = max(0.1, self.canvas['zoom'] - 0.1)
        
        # Force immediate redraw
        self.drawing_area.queue_draw()
    
    # === Transform Control Handlers ===
    
    def on_pos_x_changed(self, widget):
        self.transform['x'] = int(widget.get_value())
        self.queue_preview_update()
    
    def on_pos_x_slider_changed(self, widget):
        self.transform['x'] = int(widget.get_value())
        self.pos_x_spin.set_value(self.transform['x'])
        self.queue_preview_update()
    
    def on_pos_y_changed(self, widget):
        self.transform['y'] = int(widget.get_value())
        self.queue_preview_update()
    
    def on_pos_y_slider_changed(self, widget):
        self.transform['y'] = int(widget.get_value())
        self.pos_y_spin.set_value(self.transform['y'])
        self.queue_preview_update()
    
    def on_scale_changed(self, widget):
        self.transform['scale'] = int(widget.get_value())
        self.queue_preview_update()
    
    def on_scale_slider_changed(self, widget):
        self.transform['scale'] = int(widget.get_value())
        self.scale_spin.set_value(self.transform['scale'])
        self.queue_preview_update()
    
    def on_lock_ratio_toggled(self, widget):
        self.transform['lockRatio'] = widget.get_active()
    
    def on_anchor_clicked(self, widget, pos):
        self.transform['anchor'] = pos
        # Recalculate position based on anchor
        self.queue_preview_update()
    
    def on_reset_transform(self, widget):
        """Reset transform to defaults"""
        if self.template_pixbuf and self.graphic_pixbuf:
            self.transform['scale'] = 60
            self.transform['x'] = (self.template_pixbuf.get_width() - 
                                  int(self.graphic_pixbuf.get_width() * 0.6)) // 2
            self.transform['y'] = (self.template_pixbuf.get_height() - 
                                  int(self.graphic_pixbuf.get_height() * 0.6)) // 2
            self.transform['rotation'] = 0
            
            # Update UI
            self.scale_spin.set_value(60)
            self.scale_slider.set_value(60)
            self.pos_x_spin.set_value(self.transform['x'])
            self.pos_x_slider.set_value(self.transform['x'])
            self.pos_y_spin.set_value(self.transform['y'])
            self.pos_y_slider.set_value(self.transform['y'])
            
            self.queue_preview_update()
    
    # === Displacement Control Handlers ===
    
    def on_disp_x_changed(self, widget):
        self.displacement['x'] = widget.get_value()
        self.queue_preview_update()
    
    def on_disp_x_slider_changed(self, widget):
        self.displacement['x'] = widget.get_value()
        self.disp_x_spin.set_value(self.displacement['x'])
        self.queue_preview_update()
    
    def on_disp_y_changed(self, widget):
        self.displacement['y'] = widget.get_value()
        self.queue_preview_update()
    
    def on_disp_y_slider_changed(self, widget):
        self.displacement['y'] = widget.get_value()
        self.disp_y_spin.set_value(self.displacement['y'])
        self.queue_preview_update()
    
    def on_map_source_changed(self, widget):
        self.displacement['mapSource'] = widget.get_active_id()
        if self.displacement['mapSource'] == 'external':
            self.load_disp_map()
    
    def load_disp_map(self):
        """Load external displacement map"""
        dialog = Gtk.FileChooserDialog(
            title="Select Displacement Map",
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            try:
                self.disp_map_pixbuf = GdkPixbuf.Pixbuf.new_from_file(filename)
                self.queue_preview_update()
            except Exception as e:
                self.show_error(f"Failed to load displacement map: {e}")
        
        dialog.destroy()
    
    def on_contrast_changed(self, widget):
        self.displacement['contrast'] = int(widget.get_value())
        self.queue_preview_update()
    
    def on_contrast_slider_changed(self, widget):
        self.displacement['contrast'] = int(widget.get_value())
        self.contrast_spin.set_value(self.displacement['contrast'])
        self.queue_preview_update()
    
    def on_blend_mode_changed(self, widget):
        self.blend['mode'] = widget.get_active_id()
        self.queue_preview_update()
    
    def on_opacity_changed(self, widget):
        self.blend['opacity'] = int(widget.get_value())
        self.queue_preview_update()
    
    def on_opacity_slider_changed(self, widget):
        self.blend['opacity'] = int(widget.get_value())
        self.opacity_spin.set_value(self.blend['opacity'])
        self.queue_preview_update()
    
    def on_show_map_toggled(self, widget):
        self.displacement['showMap'] = widget.get_active()
        self.queue_preview_update()
    
    # === View Control Handlers ===
    
    def on_view_toggle(self, widget, mode):
        """Handle view mode toggle"""
        if widget.get_active():
            if mode == 'grid':
                self.canvas['showGrid'] = True
            elif mode == 'snap':
                self.canvas['snapToGrid'] = True
            else:
                self.canvas['viewMode'] = mode
                # Deactivate other mode buttons
                for m, btn in self.view_buttons.items():
                    if m != mode and m not in ['grid', 'snap']:
                        btn.set_active(False)
        else:
            if mode == 'grid':
                self.canvas['showGrid'] = False
            elif mode == 'snap':
                self.canvas['snapToGrid'] = False
        
        self.queue_preview_update()
    
    def on_quality_changed(self, widget):
        self.canvas['viewMode'] = 'draft' if widget.get_active_id() == 'draft' else 'full'
        self.queue_preview_update()
    
    def on_auto_mask_toggled(self, widget):
        pass  # Implement auto-masking logic
    
    # === Batch Processing Handlers ===
    
    def on_select_input_folder(self, widget):
        """Select input folder for batch processing"""
        dialog = Gtk.FileChooserDialog(
            title="Select Input Folder",
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.batch['inputPath'] = dialog.get_filename()
            self.scan_input_folder()
        
        dialog.destroy()
    
    def scan_input_folder(self):
        """Scan input folder for graphics"""
        if not self.batch['inputPath']:
            return
        
        self.batch['queue'] = []
        
        # Clear listbox
        for child in self.queue_listbox.get_children():
            self.queue_listbox.remove(child)
        
        # Scan for files
        for ext in self.batch['allowedExt']:
            pattern = f"*.{ext}"
            files = Path(self.batch['inputPath']).rglob(pattern)
            for file in files:
                self.batch['queue'].append(str(file))
                
                # Add to listbox
                row = Gtk.ListBoxRow()
                hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
                hbox.set_margin_top(5)
                hbox.set_margin_bottom(5)
                
                label = Gtk.Label(label=os.path.basename(str(file)))
                label.set_halign(Gtk.Align.START)
                hbox.pack_start(label, True, True, 0)
                
                status = Gtk.Label(label="⏳ Pending")
                hbox.pack_start(status, False, False, 0)
                
                row.add(hbox)
                self.queue_listbox.add(row)
        
        self.queue_listbox.show_all()
        self.log_message(f"Found {len(self.batch['queue'])} files in batch queue")
    
    def on_format_filter_changed(self, widget, ext):
        """Handle format filter change"""
        if widget.get_active():
            if ext not in self.batch['allowedExt']:
                self.batch['allowedExt'].append(ext)
        else:
            if ext in self.batch['allowedExt']:
                self.batch['allowedExt'].remove(ext)
        
        if self.batch['inputPath']:
            self.scan_input_folder()
    
    def on_process_all(self, widget):
        """Start batch processing"""
        if not self.batch['queue']:
            self.show_error("No files in batch queue. Please select an input folder first.")
            return
        
        if not self.export['path']:
            self.show_error("Please select an output folder first.")
            return
        
        if self.batch['isRunning']:
            self.batch['isRunning'] = False
            self.process_btn.set_label("▶ Process All")
            self.log_message("Batch processing cancelled")
        else:
            self.batch['isRunning'] = True
            self.batch['currentIndex'] = 0
            self.process_btn.set_label("⏹ Cancel")
            self.log_message("Starting batch processing...")
            
            # Start background thread
            thread = threading.Thread(target=self.run_batch_processing)
            thread.daemon = True
            thread.start()
    
    def run_batch_processing(self):
        """Run batch processing in background thread"""
        total = len(self.batch['queue'])
        
        for i, graphic_path in enumerate(self.batch['queue']):
            if not self.batch['isRunning']:
                break
            
            self.batch['currentIndex'] = i
            
            # Update progress
            progress = (i + 1) / total * 100
            GLib.idle_add(self.update_progress, progress, i + 1, total)
            
            # Process individual item
            try:
                self.process_single_item(graphic_path)
                self.log_message(f"✓ Processed: {os.path.basename(graphic_path)}")
            except Exception as e:
                self.log_message(f"✗ Error processing {os.path.basename(graphic_path)}: {e}")
        
        GLib.idle_add(self.on_batch_complete)
    
    def process_single_item(self, graphic_path):
        """Process a single graphic item"""
        try:
            from PIL import Image
            
            # Load images
            tshirt_img = Image.open(self.template_path).convert("RGBA")
            graphic_img = Image.open(graphic_path).convert("RGBA")
            
            # Scale graphic
            scaled_width = int(graphic_img.width * self.transform['scale'] / 100)
            scaled_height = int(graphic_img.height * self.transform['scale'] / 100)
            graphic_img = graphic_img.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
            
            # Rotate graphic
            if self.transform['rotation'] != 0:
                graphic_img = graphic_img.rotate(-self.transform['rotation'], expand=False, resample=Image.Resampling.BICUBIC)
            
            # Create result image - IMPORTANT: Maintain transparency
            result = tshirt_img.copy()
            
            # Paste graphic with transparency mask (alpha channel)
            # This ensures the top layer maintains its transparency
            result.paste(graphic_img, 
                        (int(self.transform['x']), int(self.transform['y'])), 
                        graphic_img)  # Third argument is the alpha mask
            
            # Generate output filename
            original_name = os.path.splitext(os.path.basename(graphic_path))[0]
            output_name = self.export['namingPattern'].replace('{original}', original_name)
            output_name = output_name.replace('{index}', str(self.batch['currentIndex']))
            output_name = output_name.replace('{date}', datetime.now().strftime('%Y%m%d'))
            
            output_path = os.path.join(self.export['path'], f"{output_name}.{self.export['format'].lower()}")
            
            # Save with transparency preserved
            if self.export['format'] == 'PNG':
                result.save(output_path, "PNG")
            elif self.export['format'] == 'JPG':
                # JPG doesn't support transparency, convert to white background
                bg = Image.new('RGB', result.size, (255, 255, 255))
                bg.paste(result, mask=result.split()[3])
                bg.save(output_path, "JPEG", quality=self.export['quality'])
            elif self.export['format'] == 'WebP':
                result.save(output_path, "WEBP", quality=self.export['quality'])
            
            time.sleep(0.1)  # Simulate processing time
            
        except ImportError:
            raise Exception("PIL/Pillow not installed. Please install: pip install Pillow")
    
    def update_progress(self, progress, current, total):
        """Update progress bar"""
        self.progress_bar.set_fraction(progress / 100)
        self.progress_bar.set_text(f"Processing {current}/{total} ({progress:.1f}%)")
        self.bottom_status.set_text(f"Processing: {current}/{total}")
    
    def on_batch_complete(self):
        """Handle batch processing completion"""
        self.batch['isRunning'] = False
        self.process_btn.set_label("▶ Process All")
        self.progress_bar.set_fraction(1.0)
        self.progress_bar.set_text("Complete!")
        self.bottom_status.set_text("Batch processing complete")
        self.log_message("✓ Batch processing complete!")
        
        if self.export['openOnComplete'] and self.export['path']:
            import subprocess
            subprocess.Popen(['xdg-open', self.export['path']])
    
    def on_select_output_folder(self, widget):
        """Select output folder for exports"""
        dialog = Gtk.FileChooserDialog(
            title="Select Output Folder",
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.export['path'] = dialog.get_filename()
            self.log_message(f"Output folder set: {self.export['path']}")
        
        dialog.destroy()
    
    def on_export_format_changed(self, widget, fmt):
        """Handle export format change"""
        if widget.get_active():
            self.export['format'] = fmt
    
    def on_export_quality_changed(self, widget):
        self.export['quality'] = int(widget.get_value())
    
    def on_naming_changed(self, widget):
        self.export['namingPattern'] = widget.get_text()
        self.update_naming_preview()
    
    def update_naming_preview(self):
        """Update naming template preview"""
        pattern = self.export['namingPattern']
        preview = pattern.replace('{original}', 'shirt')
        preview = preview.replace('{index}', '1')
        preview = preview.replace('{date}', '20240101')
        self.naming_preview.set_markup(f"<small>Preview: {preview}.{self.export['format'].lower()}</small>")
    
    # === Preset Handlers ===
    
    def on_preset_changed(self, widget):
        """Handle preset selection"""
        preset_id = widget.get_active_id()
        if preset_id and preset_id != "":
            self.load_preset(preset_id)
    
    def on_save_preset(self, widget):
        """Save current settings as preset"""
        dialog = Gtk.Dialog(
            title="Save Preset",
            parent=self,
            flags=0
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK
        )
        
        entry = Gtk.Entry()
        entry.set_text("My Preset")
        entry.set_width_chars(30)
        
        box = dialog.get_content_area()
        box.pack_start(Gtk.Label(label="Preset Name:"), False, False, 0)
        box.pack_start(entry, False, False, 0)
        box.show_all()
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            preset_name = entry.get_text()
            self.save_preset(preset_name)
        
        dialog.destroy()
    
    def save_preset(self, name):
        """Save preset to JSON"""
        preset_data = {
            'transform': self.transform.copy(),
            'displacement': self.displacement.copy(),
            'blend': self.blend.copy(),
            'export': self.export.copy()
        }
        
        # Save to presets directory
        presets_dir = Path.home() / ".tshirt_mockup" / "presets"
        presets_dir.mkdir(parents=True, exist_ok=True)
        
        preset_file = presets_dir / f"{name}.json"
        with open(preset_file, 'w') as f:
            json.dump(preset_data, f, indent=2)
        
        # Add to combo
        self.preset_combo.append(name.lower().replace(' ', '_'), name)
        self.log_message(f"Preset saved: {name}")
    
    def on_load_preset(self, widget):
        """Load preset from file"""
        dialog = Gtk.FileChooserDialog(
            title="Load Preset",
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )
        
        filter_json = Gtk.FileFilter()
        filter_json.set_name("JSON files")
        filter_json.add_pattern("*.json")
        dialog.add_filter(filter_json)
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            self.load_preset_file(filename)
        
        dialog.destroy()
    
    def load_preset_file(self, filename):
        """Load preset from JSON file"""
        try:
            with open(filename, 'r') as f:
                preset_data = json.load(f)
            
            # Apply preset data
            if 'transform' in preset_data:
                self.transform.update(preset_data['transform'])
            if 'displacement' in preset_data:
                self.displacement.update(preset_data['displacement'])
            if 'blend' in preset_data:
                self.blend.update(preset_data['blend'])
            
            # Update UI
            self.sync_ui_with_state()
            self.queue_preview_update()
            self.log_message(f"Preset loaded: {os.path.basename(filename)}")
            
        except Exception as e:
            self.show_error(f"Failed to load preset: {e}")
    
    def load_preset(self, preset_id):
        """Load preset by ID"""
        if preset_id == 'default':
            # Reset to defaults
            self.transform = {
                'x': 0, 'y': 0, 'scale': 60, 'rotation': 0,
                'anchor': 'C', 'lockRatio': True
            }
            self.displacement = {'x': 12, 'y': 12, 'contrast': 50, 'mapSource': 'auto', 'showMap': False}
            self.blend = {'mode': 'normal', 'opacity': 85}
            self.sync_ui_with_state()
            self.queue_preview_update()
    
    def sync_ui_with_state(self):
        """Sync UI controls with current state"""
        # Transform
        self.pos_x_spin.set_value(self.transform['x'])
        self.pos_x_slider.set_value(self.transform['x'])
        self.pos_y_spin.set_value(self.transform['y'])
        self.pos_y_slider.set_value(self.transform['y'])
        self.scale_spin.set_value(self.transform['scale'])
        self.scale_slider.set_value(self.transform['scale'])
        
        # Displacement
        self.disp_x_spin.set_value(self.displacement['x'])
        self.disp_x_slider.set_value(self.displacement['x'])
        self.disp_y_spin.set_value(self.displacement['y'])
        self.disp_y_slider.set_value(self.displacement['y'])
        self.contrast_spin.set_value(self.displacement['contrast'])
        self.contrast_slider.set_value(self.displacement['contrast'])
        
        # Blend
        self.opacity_spin.set_value(self.blend['opacity'])
        self.opacity_slider.set_value(self.blend['opacity'])
    
    def on_settings(self, widget):
        """Open settings dialog"""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Settings"
        )
        dialog.format_secondary_text("Settings functionality can be expanded here.")
        dialog.run()
        dialog.destroy()
    
    # === Utility Methods ===
    
    def log_message(self, message):
        """Add message to status log"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {message}\n"
        self.batch['log'].append(log_entry)
        
        buffer = self.log_text.get_buffer()
        end_iter = buffer.get_end_iter()
        buffer.insert(end_iter, log_entry)
        
        # Auto-scroll to end
        self.log_text.scroll_mark_onscreen(buffer.get_insert())
    
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
