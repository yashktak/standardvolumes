import glfw
import numpy as np
import math
from OpenGL.GL import *
from OpenGL.GLU import *
import pygame  # Added for text rendering

class Camera:
    def __init__(self):
        self.position = [0.0, 10.0, 20.0]  # Position camera higher and further back
        self.target = [0.0, 0.0, 0.0]      # Looking at origin
        self.up = [0.0, 1.0, 0.0]          # Up vector
        self.last_x = 0
        self.last_y = 0
        self.first_mouse = True
        self.sensitivity = 0.5             # Increased sensitivity
        self.zoom_factor = 1.0             # Zoom level
        self.orbit_radius = 20.0           # Distance from target
        self.orbit_angle_h = 0.0           # Horizontal orbit angle
        self.orbit_angle_v = 45.0          # Vertical orbit angle
        self.pan_sensitivity = 0.05        # Pan sensitivity

    def update_camera_vectors(self):
        # Calculate orbit position
        y = self.orbit_radius * math.sin(math.radians(self.orbit_angle_v))
        radius_xz = self.orbit_radius * math.cos(math.radians(self.orbit_angle_v))
        x = radius_xz * math.cos(math.radians(self.orbit_angle_h))
        z = radius_xz * math.sin(math.radians(self.orbit_angle_h))
        
        # Update camera position
        self.position = [
            self.target[0] + x,
            self.target[1] + y,
            self.target[2] + z
        ]

    def process_orbit(self, dx, dy):
        # Update orbit angles based on mouse movement
        self.orbit_angle_h += dx * self.sensitivity
        self.orbit_angle_v += dy * self.sensitivity
        
        # Clamp vertical angle to prevent flipping
        if self.orbit_angle_v > 89.0:
            self.orbit_angle_v = 89.0
        if self.orbit_angle_v < -89.0:
            self.orbit_angle_v = -89.0
            
        self.update_camera_vectors()

    def process_pan(self, dx, dy):
        # Get right and up vectors in world space
        forward = np.array([
            self.target[0] - self.position[0],
            self.target[1] - self.position[1],
            self.target[2] - self.position[2]
        ])
        forward = forward / np.linalg.norm(forward)
        
        world_up = np.array([0.0, 1.0, 0.0])
        right = np.cross(forward, world_up)
        right = right / np.linalg.norm(right)
        
        up = np.cross(right, forward)
        up = up / np.linalg.norm(up)
        
        # Scale movement by distance to make panning consistent at any zoom level
        pan_scale = self.orbit_radius * self.pan_sensitivity
        
        # Calculate pan amounts
        right_amount = right * dx * pan_scale
        up_amount = up * dy * pan_scale
        
        # Update target and position
        for i in range(3):
            self.target[i] -= right_amount[i] - up_amount[i]
            self.position[i] -= right_amount[i] - up_amount[i]

    def process_zoom(self, amount):
        # Update orbit radius (zoom)
        self.orbit_radius -= amount * self.orbit_radius * 0.1
        
        # Clamp orbit radius to prevent getting too close or too far
        if self.orbit_radius < 1.0:
            self.orbit_radius = 1.0
        if self.orbit_radius > 100.0:
            self.orbit_radius = 100.0
            
        self.update_camera_vectors()

    def apply_view(self):
        glLoadIdentity()
        gluLookAt(
            self.position[0], self.position[1], self.position[2],
            self.target[0], self.target[1], self.target[2],
            self.up[0], self.up[1], self.up[2]
        )

    def get_view_name(self):
        """Return a name for the current view based on the orbit angles"""
        # Normalize the horizontal angle to 0-360 range
        h_angle = self.orbit_angle_h % 360
        if h_angle < 0:
            h_angle += 360
            
        # Define quadrants for cardinal directions
        if 45 <= h_angle < 135:
            direction = "Front"
        elif 135 <= h_angle < 225:
            direction = "Right"
        elif 225 <= h_angle < 315:
            direction = "Back"
        else:  # 315 <= h_angle < 45
            direction = "Left"
            
        # Add top/bottom qualifier based on vertical angle
        if self.orbit_angle_v >= 60:
            qualifier = "Top"
        elif self.orbit_angle_v <= -60:
            qualifier = "Bottom"
        else:
            qualifier = ""
            
        # Combine qualifiers
        if qualifier:
            return f"{qualifier} {direction}"
        return direction


class CADPlatform:
    def __init__(self):
        self.camera = Camera()
        self.left_mouse_pressed = False
        self.middle_mouse_pressed = False
        self.right_mouse_pressed = False
        self.last_x = 0
        self.last_y = 0
        self.grid_size = 100  # Using 100 to match the -100 to 100 range
        self.grid_spacing = 1  # Grid line spacing
        self.font = None  # For text rendering
        
    def initialize(self):
        if not glfw.init():
            print("Failed to initialize GLFW")
            return False
            
        # Get primary monitor
        monitor = glfw.get_primary_monitor()
        mode = glfw.get_video_mode(monitor)
        
        # Create a full-screen window
        self.window = glfw.create_window(mode.size.width, mode.size.height, "AutoCAD-Style Platform", monitor, None)
        
        if not self.window:
            glfw.terminate()
            print("Failed to create GLFW window")
            return False
            
        # Make the window's context current
        glfw.make_context_current(self.window)
        
        # Get the actual framebuffer size (for high DPI displays)
        self.width, self.height = glfw.get_framebuffer_size(self.window)
        
        # Set callbacks
        glfw.set_framebuffer_size_callback(self.window, self.framebuffer_size_callback)
        glfw.set_cursor_pos_callback(self.window, self.mouse_callback)
        glfw.set_mouse_button_callback(self.window, self.mouse_button_callback)
        glfw.set_scroll_callback(self.window, self.scroll_callback)
        glfw.set_key_callback(self.window, self.key_callback)
        
        # Set up OpenGL
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LINE_SMOOTH)  # Enable line anti-aliasing
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glClearColor(0.1, 0.1, 0.1, 1.0)  # Darker background
        
        # Set up projection matrix
        self.update_projection()
        
        # Initialize camera
        self.camera.update_camera_vectors()
        
        # Initialize pygame for text rendering
        pygame.init()
        self.font = pygame.font.SysFont('Arial', 24)  # Choose a font and size
        
        return True
        
    def update_projection(self):
        aspect = self.width / self.height
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, aspect, 0.1, 1000.0)
        glMatrixMode(GL_MODELVIEW)
        
    def framebuffer_size_callback(self, window, width, height):
        self.width = width
        self.height = height
        glViewport(0, 0, width, height)
        self.update_projection()
        
    def mouse_callback(self, window, x_pos, y_pos):
        if self.left_mouse_pressed or self.middle_mouse_pressed or self.right_mouse_pressed:
            # Calculate the difference in mouse position
            dx = x_pos - self.last_x
            dy = self.last_y - y_pos  # Reversed since y-coordinates range from bottom to top
            
            if self.left_mouse_pressed:
                # Orbit camera around target
                self.camera.process_orbit(dx, dy)
            elif self.middle_mouse_pressed:
                # Pan camera
                self.camera.process_pan(dx, dy)
            elif self.right_mouse_pressed:
                # Vertical pan only (for quick height adjustment)
                self.camera.process_pan(0, dy)
            
        self.last_x = x_pos
        self.last_y = y_pos
            
    def mouse_button_callback(self, window, button, action, mods):
        if button == glfw.MOUSE_BUTTON_LEFT:
            if action == glfw.PRESS:
                self.left_mouse_pressed = True
                x, y = glfw.get_cursor_pos(self.window)
                self.last_x = x
                self.last_y = y
            elif action == glfw.RELEASE:
                self.left_mouse_pressed = False
                
        elif button == glfw.MOUSE_BUTTON_MIDDLE:
            if action == glfw.PRESS:
                self.middle_mouse_pressed = True
                x, y = glfw.get_cursor_pos(self.window)
                self.last_x = x
                self.last_y = y
            elif action == glfw.RELEASE:
                self.middle_mouse_pressed = False
                
        elif button == glfw.MOUSE_BUTTON_RIGHT:
            if action == glfw.PRESS:
                self.right_mouse_pressed = True
                x, y = glfw.get_cursor_pos(self.window)
                self.last_x = x
                self.last_y = y
            elif action == glfw.RELEASE:
                self.right_mouse_pressed = False
                
    def scroll_callback(self, window, x_offset, y_offset):
        self.camera.process_zoom(y_offset)
        
    def key_callback(self, window, key, scancode, action, mods):
        if key == glfw.KEY_ESCAPE and action == glfw.PRESS:
            glfw.set_window_should_close(window, True)
        elif key == glfw.KEY_HOME and action == glfw.PRESS:
            # Reset view
            self.camera = Camera()
            self.camera.update_camera_vectors()
        elif key == glfw.KEY_F and action == glfw.PRESS:
            # Toggle fullscreen
            if glfw.get_window_monitor(window) is None:
                monitor = glfw.get_primary_monitor()
                mode = glfw.get_video_mode(monitor)
                glfw.set_window_monitor(window, monitor, 0, 0, 
                                        mode.size.width, mode.size.height, 
                                        mode.refresh_rate)
            else:
                monitor = glfw.get_primary_monitor()
                mode = glfw.get_video_mode(monitor)
                glfw.set_window_monitor(window, None, 100, 100, 
                                        int(mode.size.width * 0.8), 
                                        int(mode.size.height * 0.8), 
                                        0)
            # Update framebuffer size
            self.width, self.height = glfw.get_framebuffer_size(self.window)
            self.update_projection()
            
    def draw_grid(self):
        major_grid_spacing = 10  # Spacing for darker/major grid lines
        
        # Draw the grid on the XZ plane from -100 to 100
        glBegin(GL_LINES)
        
        # Draw Z lines (along X axis)
        for i in range(-self.grid_size, self.grid_size + 1, self.grid_spacing):
            # Skip the axis as it will be drawn separately
            if i == 0:
                continue
                
            # Determine if this is a major grid line
            is_major = (i % major_grid_spacing) == 0
            
            # Calculate fade based on distance from center
            fade = max(0.2, 1.0 - (abs(i) / self.grid_size) * 0.8)
            
            if is_major:
                # Darker, more visible lines for major grid
                glColor4f(0.6, 0.6, 0.6, fade)
            else:
                # Lighter lines for minor grid
                glColor4f(0.3, 0.3, 0.3, fade * 0.8)
            
            glVertex3f(-self.grid_size, 0, i)
            glVertex3f(self.grid_size, 0, i)
        
        # Draw X lines (along Z axis)
        for i in range(-self.grid_size, self.grid_size + 1, self.grid_spacing):
            # Skip the axis as it will be drawn separately
            if i == 0:
                continue
                
            # Determine if this is a major grid line
            is_major = (i % major_grid_spacing) == 0
            
            # Calculate fade based on distance from center
            fade = max(0.2, 1.0 - (abs(i) / self.grid_size) * 0.8)
            
            if is_major:
                # Darker, more visible lines for major grid
                glColor4f(0.6, 0.6, 0.6, fade)
            else:
                # Lighter lines for minor grid
                glColor4f(0.3, 0.3, 0.3, fade * 0.8)
            
            glVertex3f(i, 0, -self.grid_size)
            glVertex3f(i, 0, self.grid_size)
        
        glEnd()
        
        # Draw grid points at integer coordinates
        self.draw_grid_points()
        
    def draw_grid_points(self):
        """Draw points at integer grid intersections"""
        glPointSize(2.0)
        glBegin(GL_POINTS)
        
        # Draw points at each grid intersection
        for x in range(-self.grid_size, self.grid_size + 1, 5):  # Draw points every 5 units to avoid clutter
            for z in range(-self.grid_size, self.grid_size + 1, 5):
                # Skip drawing at the axes
                if x == 0 and z == 0:
                    continue
                    
                # Calculate fade based on distance from center
                distance = math.sqrt(x*x + z*z)
                fade = max(0.3, 1.0 - (distance / (self.grid_size * 1.414)) * 0.7)
                
                # Draw point
                glColor4f(0.7, 0.7, 0.7, fade)
                glVertex3f(x, 0, z)
                
        glEnd()
        glPointSize(1.0)
        
    def draw_axes(self, length=100.0):  # Extended axis length to match grid size
        glLineWidth(3.0)  # Make axes thicker for better visibility
        glBegin(GL_LINES)
        
        # X-axis - Red
        glColor3f(1.0, 0.0, 0.0)
        glVertex3f(-length, 0.0, 0.0)  # Extend in negative direction
        glVertex3f(length, 0.0, 0.0)   # Extend in positive direction
        
        # Y-axis - Green
        glColor3f(0.0, 1.0, 0.0)
        glVertex3f(0.0, -length/4, 0.0)  # Shorter in negative direction
        glVertex3f(0.0, length, 0.0)     # Extend in positive direction
        
        # Z-axis - Blue
        glColor3f(0.0, 0.0, 1.0)
        glVertex3f(0.0, 0.0, -length)  # Extend in negative direction
        glVertex3f(0.0, 0.0, length)   # Extend in positive direction
        
        glEnd()
        
        # Draw axis labels
        self.draw_axis_labels(length)
        
        # Draw axis tick marks
        self.draw_axis_ticks(length)
        
        glLineWidth(1.0)
        
    def draw_axis_ticks(self, length):
        """Draw tick marks on axes"""
        tick_spacing = 10  # Draw ticks every 10 units
        tick_size = 0.5    # Size of tick marks
        
        glLineWidth(2.0)
        glBegin(GL_LINES)
        
        # X-axis ticks
        glColor3f(1.0, 0.0, 0.0)
        for i in range(-int(length), int(length) + 1, tick_spacing):
            if i == 0:
                continue  # Skip origin
            glVertex3f(i, 0, 0)
            glVertex3f(i, tick_size, 0)
            
        # Y-axis ticks
        glColor3f(0.0, 1.0, 0.0)
        for i in range(0, int(length) + 1, tick_spacing):
            if i == 0:
                continue  # Skip origin
            glVertex3f(0, i, 0)
            glVertex3f(tick_size, i, 0)
            
        # Z-axis ticks
        glColor3f(0.0, 0.0, 1.0)
        for i in range(-int(length), int(length) + 1, tick_spacing):
            if i == 0:
                continue  # Skip origin
            glVertex3f(0, 0, i)
            glVertex3f(0, tick_size, i)
            
        glEnd()
        glLineWidth(1.0)
        
    def draw_axis_labels(self, length):
        # Draw markers at the ends of axes only (removed the white cube at origin)
        
        # X-axis label (draw a small red cube at the end of X axis)
        glColor3f(1.0, 0.0, 0.0)
        glPushMatrix()
        glTranslatef(length, 0, 0)
        glScalef(2.0, 2.0, 2.0)  # Make end markers larger
        self.draw_cube()
        glPopMatrix()
        
        # Y-axis label (draw a small green cube at the end of Y axis)
        glColor3f(0.0, 1.0, 0.0)
        glPushMatrix()
        glTranslatef(0, length, 0)
        glScalef(2.0, 2.0, 2.0)  # Make end markers larger
        self.draw_cube()
        glPopMatrix()
        
        # Z-axis label (draw a small blue cube at the end of Z axis)
        glColor3f(0.0, 0.0, 1.0)
        glPushMatrix()
        glTranslatef(0, 0, length)
        glScalef(2.0, 2.0, 2.0)  # Make end markers larger
        self.draw_cube()
        glPopMatrix()
        
        # Removed the origin marker (white cube)
        
    def draw_cube(self):
        # Helper method to draw a simple cube
        vertices = [
            # Front face
            (-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5),
            # Back face
            (-0.5, -0.5, -0.5), (-0.5, 0.5, -0.5), (0.5, 0.5, -0.5), (0.5, -0.5, -0.5),
            # Top face
            (-0.5, 0.5, -0.5), (-0.5, 0.5, 0.5), (0.5, 0.5, 0.5), (0.5, 0.5, -0.5),
            # Bottom face
            (-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (0.5, -0.5, 0.5), (-0.5, -0.5, 0.5),
            # Right face
            (0.5, -0.5, -0.5), (0.5, 0.5, -0.5), (0.5, 0.5, 0.5), (0.5, -0.5, 0.5),
            # Left face
            (-0.5, -0.5, -0.5), (-0.5, -0.5, 0.5), (-0.5, 0.5, 0.5), (-0.5, 0.5, -0.5)
        ]
        
        glBegin(GL_QUADS)
        for i in range(0, len(vertices), 4):
            for j in range(4):
                glVertex3f(*vertices[i + j])
        glEnd()
    
    def draw_coordinate_labels(self):
        """Draw coordinate values along axes"""
        # This would be implemented with text rendering
        # For this example, we'll place markers at specific intervals
        pass
    
    def draw_angle_display(self):
        """Draw current camera angles and view information on screen"""
        # Switch to orthographic projection for 2D rendering
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.width, self.height, 0, -1, 1)
        
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        # Disable depth test for UI elements
        glDisable(GL_DEPTH_TEST)
        
        # Draw semi-transparent background for angle display
        margin = 20
        padding = 10
        box_width = 220
        box_height = 120
        
        # Position in the bottom-right corner
        x = self.width - box_width - margin
        y = self.height - box_height - margin
        
        # Draw background
        glColor4f(0.0, 0.0, 0.0, 0.7)  # Semi-transparent black
        glBegin(GL_QUADS)
        glVertex2f(x, y)
        glVertex2f(x + box_width, y)
        glVertex2f(x + box_width, y + box_height)
        glVertex2f(x, y + box_height)
        glEnd()
        
        # Draw border
        glColor3f(0.7, 0.7, 0.7)  # Light gray
        glBegin(GL_LINE_LOOP)
        glVertex2f(x, y)
        glVertex2f(x + box_width, y)
        glVertex2f(x + box_width, y + box_height)
        glVertex2f(x, y + box_height)
        glEnd()
        
        # Current view name
        view_name = self.camera.get_view_name()
        self.render_text(f"View: {view_name}", x + padding, y + padding)
        
        # Horizontal and vertical angles (rounded for readability)
        h_angle = round(self.camera.orbit_angle_h % 360, 1)
        if h_angle < 0:
            h_angle += 360
        v_angle = round(self.camera.orbit_angle_v, 1)
        
        self.render_text(f"H-Angle: {h_angle}°", x + padding, y + padding + 30)
        self.render_text(f"V-Angle: {v_angle}°", x + padding, y + padding + 60)
        
        # Display distance from target
        distance = round(self.camera.orbit_radius, 2)
        self.render_text(f"Distance: {distance}", x + padding, y + padding + 90)
        
        # Restore the previous matrices
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        
        # Re-enable depth test
        glEnable(GL_DEPTH_TEST)
    
    def render_text(self, text, x, y):
        """Render text at the given position using pygame"""
        # This is a basic implementation - in a production app, you'd use a more efficient method
        # like texture-mapped font rendering in OpenGL
        glColor3f(1.0, 1.0, 1.0)  # White text
        
        # Create a text surface
        text_surface = self.font.render(text, True, (255, 255, 255))
        text_data = pygame.image.tostring(text_surface, "RGBA", True)
        
        # Create an OpenGL texture
        texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, text_surface.get_width(), text_surface.get_height(), 
                    0, GL_RGBA, GL_UNSIGNED_BYTE, text_data)
        
        # Enable texturing for drawing the text
        glEnable(GL_TEXTURE_2D)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        
        # Draw the text as a textured quad
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(x, y)
        glTexCoord2f(1, 0); glVertex2f(x + text_surface.get_width(), y)
        glTexCoord2f(1, 1); glVertex2f(x + text_surface.get_width(), y + text_surface.get_height())
        glTexCoord2f(0, 1); glVertex2f(x, y + text_surface.get_height())
        glEnd()
        
        # Clean up
        glDisable(GL_TEXTURE_2D)
        glDeleteTextures(1, [texture])
        
    def draw_status_info(self):
        # Add coordinate range info to the display
        margin = 20
        padding = 10
        box_width = 220
        box_height = 60
        
        # Position in the top-left corner
        x = margin
        y = margin
        
        # Switch to orthographic projection for 2D rendering
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.width, self.height, 0, -1, 1)
        
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        # Disable depth test for UI elements
        glDisable(GL_DEPTH_TEST)
        
        # Draw background
        glColor4f(0.0, 0.0, 0.0, 0.7)  # Semi-transparent black
        glBegin(GL_QUADS)
        glVertex2f(x, y)
        glVertex2f(x + box_width, y)
        glVertex2f(x + box_width, y + box_height)
        glVertex2f(x, y + box_height)
        glEnd()
        
        # Draw border
        glColor3f(0.7, 0.7, 0.7)  # Light gray
        glBegin(GL_LINE_LOOP)
        glVertex2f(x, y)
        glVertex2f(x + box_width, y)
        glVertex2f(x + box_width, y + box_height)
        glVertex2f(x, y + box_height)
        glEnd()
        
        # Render coordinate range info
        self.render_text("Coordinate Range:", x + padding, y + padding)
        self.render_text("X, Z: -100 to 100", x + padding, y + padding + 30)
        
        # Restore the previous matrices
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        
        # Re-enable depth test
        glEnable(GL_DEPTH_TEST)
        
    def render(self):
        # Clear the screen
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        # Set model view matrix
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        # Apply camera view
        self.camera.apply_view()
        
        # Draw grid and axes
        self.draw_grid()
        self.draw_axes(100.0)  # Extended axis length to match grid size
        
        # Draw status information
        self.draw_status_info()
        
        # Draw angle display overlay
        self.draw_angle_display()
        
    def run(self):
        if not self.initialize():
            return
            
        # Main loop
        while not glfw.window_should_close(self.window):
            # Render
            self.render()
            
            # Swap front and back buffers
            glfw.swap_buffers(self.window)
            
            # Poll for and process events
            glfw.poll_events()
            
        # Clean up
        pygame.quit()
        glfw.terminate()
        
        
if __name__ == "__main__":
    cad = CADPlatform()
    cad.run()