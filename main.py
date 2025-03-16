import glfw
import numpy as np
import math
from OpenGL.GL import *
from OpenGL.GLU import *
import pygame

class Camera:
    def __init__(self):
        self.position = [0.0, 10.0, 20.0]
        self.target = [0.0, 0.0, 0.0]
        self.up = [0.0, 1.0, 0.0]
        self.last_x = 0
        self.last_y = 0
        self.first_mouse = True
        self.sensitivity = 0.5
        self.zoom_factor = 1.0
        self.orbit_radius = 20.0
        self.orbit_angle_h = 0.0
        self.orbit_angle_v = 45.0
        self.pan_sensitivity = 0.05

    def update_camera_vectors(self):
        y = self.orbit_radius * math.sin(math.radians(self.orbit_angle_v))
        radius_xz = self.orbit_radius * math.cos(math.radians(self.orbit_angle_v))
        x = radius_xz * math.cos(math.radians(self.orbit_angle_h))
        z = radius_xz * math.sin(math.radians(self.orbit_angle_h))
        self.position = [self.target[0] + x, self.target[1] + y, self.target[2] + z]

    def process_orbit(self, dx, dy):
        self.orbit_angle_h += dx * self.sensitivity
        self.orbit_angle_v += dy * self.sensitivity
        if self.orbit_angle_v > 89.0:
            self.orbit_angle_v = 89.0
        if self.orbit_angle_v < 0.0:
            self.orbit_angle_v = 0.0
        self.update_camera_vectors()

    def process_pan(self, dx, dy):
        forward = np.array([self.target[0] - self.position[0],
                            self.target[1] - self.position[1],
                            self.target[2] - self.position[2]])
        forward = forward / np.linalg.norm(forward)
        world_up = np.array([0.0, 1.0, 0.0])
        right = np.cross(forward, world_up)
        right = right / np.linalg.norm(right)
        up = np.cross(right, forward)
        up = up / np.linalg.norm(up)
        pan_scale = self.orbit_radius * self.pan_sensitivity
        right_amount = right * dx * pan_scale
        up_amount = up * dy * pan_scale
        movement = -right_amount + up_amount
        movement[1] = 0
        for i in range(3):
            self.target[i] += movement[i]
            self.position[i] += movement[i]

    def process_zoom(self, amount):
        self.orbit_radius -= amount * self.orbit_radius * 0.1
        if self.orbit_radius < 1.0:
            self.orbit_radius = 1.0
        if self.orbit_radius > 100.0:
            self.orbit_radius = 100.0
        self.update_camera_vectors()

    def apply_view(self):
        glLoadIdentity()
        gluLookAt(self.position[0], self.position[1], self.position[2],
                  self.target[0], self.target[1], self.target[2],
                  self.up[0], self.up[1], self.up[2])

    def get_view_name(self):
        h_angle = self.orbit_angle_h % 360
        if h_angle < 0:
            h_angle += 360
        if 45 <= h_angle < 135:
            direction = "Front"
        elif 135 <= h_angle < 225:
            direction = "Right"
        elif 225 <= h_angle < 315:
            direction = "Back"
        else:
            direction = "Left"
        qualifier = "Top" if self.orbit_angle_v >= 60 else ""
        return f"{qualifier} {direction}" if qualifier else direction

class CADPlatform:
    def __init__(self):
        self.camera = Camera()
        self.left_mouse_pressed = False
        self.middle_mouse_pressed = False
        self.right_mouse_pressed = False
        self.last_x = 0
        self.last_y = 0
        self.grid_size = 100
        self.grid_spacing = 1
        self.font = None
        # Added visibility flags, initially True
        self.axes_visible = True
        self.labels_visible = True

    def initialize(self):
        if not glfw.init():
            print("Failed to initialize GLFW")
            return False
        monitor = glfw.get_primary_monitor()
        mode = glfw.get_video_mode(monitor)
        self.window = glfw.create_window(mode.size.width, mode.size.height, "AutoCAD-Style Platform", monitor, None)
        if not self.window:
            glfw.terminate()
            print("Failed to create GLFW window")
            return False
        glfw.make_context_current(self.window)
        self.width, self.height = glfw.get_framebuffer_size(self.window)
        glfw.set_framebuffer_size_callback(self.window, self.framebuffer_size_callback)
        glfw.set_cursor_pos_callback(self.window, self.mouse_callback)
        glfw.set_mouse_button_callback(self.window, self.mouse_button_callback)
        glfw.set_scroll_callback(self.window, self.scroll_callback)
        glfw.set_key_callback(self.window, self.key_callback)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LINE_SMOOTH)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glClearColor(0.1, 0.1, 0.1, 1.0)
        self.update_projection()
        self.camera.update_camera_vectors()
        pygame.init()
        self.font = pygame.font.SysFont('Arial', 24)
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
            dx = x_pos - self.last_x
            dy = self.last_y - y_pos
            if self.left_mouse_pressed:
                self.camera.process_orbit(dx, dy)
            elif self.middle_mouse_pressed:
                self.camera.process_pan(dx, dy)
            elif self.right_mouse_pressed:
                self.camera.process_pan(0, dy)
        self.last_x = x_pos
        self.last_y = y_pos

    def mouse_button_callback(self, window, button, action, mods):
        if button == glfw.MOUSE_BUTTON_LEFT:
            self.left_mouse_pressed = action == glfw.PRESS
        elif button == glfw.MOUSE_BUTTON_MIDDLE:
            self.middle_mouse_pressed = action == glfw.PRESS
        elif button == glfw.MOUSE_BUTTON_RIGHT:
            self.right_mouse_pressed = action == glfw.PRESS
        if action == glfw.PRESS:
            x, y = glfw.get_cursor_pos(self.window)
            self.last_x = x
            self.last_y = y

    def scroll_callback(self, window, x_offset, y_offset):
        self.camera.process_zoom(y_offset)

    def key_callback(self, window, key, scancode, action, mods):
        if key == glfw.KEY_ESCAPE and action == glfw.PRESS:
            glfw.set_window_should_close(window, True)
        elif key == glfw.KEY_HOME and action == glfw.PRESS:
            self.camera = Camera()
            self.camera.update_camera_vectors()
        elif key == glfw.KEY_F and action == glfw.PRESS:
            if glfw.get_window_monitor(window) is None:
                monitor = glfw.get_primary_monitor()
                mode = glfw.get_video_mode(monitor)
                glfw.set_window_monitor(window, monitor, 0, 0, mode.size.width, mode.size.height, mode.refresh_rate)
            else:
                monitor = glfw.get_primary_monitor()
                mode = glfw.get_video_mode(monitor)
                glfw.set_window_monitor(window, None, 100, 100, int(mode.size.width * 0.8), int(mode.size.height * 0.8), 0)
            self.width, self.height = glfw.get_framebuffer_size(self.window)
            self.update_projection()
        # Added key handlers for "A" and "W"
        elif key == glfw.KEY_A and action == glfw.PRESS:
            self.axes_visible = not self.axes_visible
        elif key == glfw.KEY_W and action == glfw.PRESS:
            self.labels_visible = not self.labels_visible

    def draw_grid(self):
        major_grid_spacing = 10
        glBegin(GL_LINES)
        for i in range(-self.grid_size, self.grid_size + 1, self.grid_spacing):
            if i == 0:
                continue
            is_major = (i % major_grid_spacing) == 0
            fade = max(0.2, 1.0 - (abs(i) / self.grid_size) * 0.8)
            glColor4f(0.6 if is_major else 0.3, 0.6 if is_major else 0.3, 0.6 if is_major else 0.3, fade * (1.0 if is_major else 0.8))
            glVertex3f(-self.grid_size, 0, i)
            glVertex3f(self.grid_size, 0, i)
            glVertex3f(i, 0, -self.grid_size)
            glVertex3f(i, 0, self.grid_size)
        glEnd()
        self.draw_grid_points()

    def draw_grid_points(self):
        glPointSize(2.0)
        glBegin(GL_POINTS)
        for x in range(-self.grid_size, self.grid_size + 1, 5):
            for z in range(-self.grid_size, self.grid_size + 1, 5):
                if x == 0 and z == 0:
                    continue
                distance = math.sqrt(x*x + z*z)
                fade = max(0.3, 1.0 - (distance / (self.grid_size * 1.414)) * 0.7)
                glColor4f(0.7, 0.7, 0.7, fade)
                glVertex3f(x, 0, z)
        glEnd()
        glPointSize(1.0)

    def draw_axes(self, length=100.0):
        glLineWidth(3.0)
        glBegin(GL_LINES)
        glColor3f(1.0, 0.0, 0.0)
        glVertex3f(-length, 0.0, 0.0)
        glVertex3f(length, 0.0, 0.0)
        glColor3f(0.0, 1.0, 0.0)
        glVertex3f(0.0, 0.0, 0.0)
        glVertex3f(0.0, length, 0.0)
        glColor3f(0.0, 0.0, 1.0)
        glVertex3f(0.0, 0.0, -length)
        glVertex3f(0.0, 0.0, length)
        glEnd()
        self.draw_axis_labels(length)
        self.draw_axis_ticks(length)
        glLineWidth(1.0)

    def draw_axis_ticks(self, length):
        tick_spacing = 10
        tick_size = 0.5
        glLineWidth(2.0)
        glBegin(GL_LINES)
        glColor3f(1.0, 0.0, 0.0)
        for i in range(-int(length), int(length) + 1, tick_spacing):
            glVertex3f(i, 0, 0)
            glVertex3f(i, tick_size, 0)
        glColor3f(0.0, 1.0, 0.0)
        for i in range(0, int(length) + 1, tick_spacing):
            glVertex3f(0, i, 0)
            glVertex3f(tick_size, i, 0)
        glColor3f(0.0, 0.0, 1.0)
        for i in range(-int(length), int(length) + 1, tick_spacing):
            glVertex3f(0, 0, i)
            glVertex3f(0, tick_size, i)
        glEnd()
        glLineWidth(1.0)

    def draw_axis_labels(self, length):
        glColor3f(1.0, 0.0, 0.0)
        glPushMatrix()
        glTranslatef(length, 0, 0)
        glScalef(2.0, 2.0, 2.0)
        self.draw_cube()
        glPopMatrix()
        glColor3f(0.0, 1.0, 0.0)
        glPushMatrix()
        glTranslatef(0, length, 0)
        glScalef(2.0, 2.0, 2.0)
        self.draw_cube()
        glPopMatrix()
        glColor3f(0.0, 0.0, 1.0)
        glPushMatrix()
        glTranslatef(0, 0, length)
        glScalef(2.0, 2.0, 2.0)
        self.draw_cube()
        glPopMatrix()

    def draw_cube(self):
        vertices = [
            (-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5),
            (-0.5, -0.5, -0.5), (-0.5, 0.5, -0.5), (0.5, 0.5, -0.5), (0.5, -0.5, -0.5),
            (-0.5, 0.5, -0.5), (-0.5, 0.5, 0.5), (0.5, 0.5, 0.5), (0.5, 0.5, -0.5),
            (-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (0.5, -0.5, 0.5), (-0.5, -0.5, 0.5),
            (0.5, -0.5, -0.5), (0.5, 0.5, -0.5), (0.5, 0.5, 0.5), (0.5, -0.5, 0.5),
            (-0.5, -0.5, -0.5), (-0.5, -0.5, 0.5), (-0.5, 0.5, 0.5), (-0.5, 0.5, -0.5)
        ]
        glBegin(GL_QUADS)
        for i in range(0, len(vertices), 4):
            for j in range(4):
                glVertex3f(*vertices[i + j])
        glEnd()

    def draw_coordinate_labels(self):
        modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
        projection = glGetDoublev(GL_PROJECTION_MATRIX)
        viewport = glGetIntegerv(GL_VIEWPORT)
        tick_spacing = 10
        length = 100.0
        def project_and_collect(axis, start, end, step):
            labels = []
            for i in range(start, end + 1, step):
                pos = (i, 0, 0) if axis == 'x' else (0, i, 0) if axis == 'y' else (0, 0, i)
                win_x, win_y, win_z = gluProject(pos[0], pos[1], pos[2], modelview, projection, viewport)
                if 0 <= win_x <= viewport[2] and 0 <= win_y <= viewport[3] and win_z < 1.0:
                    labels.append((win_x, win_y, str(i)))
            return labels
        x_labels = project_and_collect('x', -int(length), int(length), tick_spacing)
        y_labels = project_and_collect('y', 0, int(length), tick_spacing)
        z_labels = project_and_collect('z', -int(length), int(length), tick_spacing)
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.width, self.height, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glDisable(GL_DEPTH_TEST)
        offset = 10
        for win_x, win_y, label in x_labels:
            self.render_text(label, win_x, self.height - win_y + offset)
        for win_x, win_y, label in y_labels:
            self.render_text(label, win_x - 20, self.height - win_y)
        for win_x, win_y, label in z_labels:
            self.render_text(label, win_x, self.height - win_y + offset)
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        glEnable(GL_DEPTH_TEST)

    def draw_angle_display(self):
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.width, self.height, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glDisable(GL_DEPTH_TEST)
        margin = 20
        padding = 10
        box_width = 220
        box_height = 120
        x = self.width - box_width - margin
        y = self.height - box_height - margin
        glColor4f(0.0, 0.0, 0.0, 0.7)
        glBegin(GL_QUADS)
        glVertex2f(x, y)
        glVertex2f(x + box_width, y)
        glVertex2f(x + box_width, y + box_height)
        glVertex2f(x, y + box_height)
        glEnd()
        glColor3f(0.7, 0.7, 0.7)
        glBegin(GL_LINE_LOOP)
        glVertex2f(x, y)
        glVertex2f(x + box_width, y)
        glVertex2f(x + box_width, y + box_height)
        glVertex2f(x, y + box_height)
        glEnd()
        view_name = self.camera.get_view_name()
        self.render_text(f"View: {view_name}", x + padding, y + padding)
        h_angle = round(self.camera.orbit_angle_h % 360, 1)
        if h_angle < 0:
            h_angle += 360
        v_angle = round(self.camera.orbit_angle_v, 1)
        self.render_text(f"H-Angle: {h_angle}°", x + padding, y + padding + 30)
        self.render_text(f"V-Angle: {v_angle}°", x + padding, y + padding + 60)
        distance = round(self.camera.orbit_radius, 2)
        self.render_text(f"Distance: {distance}", x + padding, y + padding + 90)
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        glEnable(GL_DEPTH_TEST)

    def render_text(self, text, x, y):
        glColor3f(1.0, 1.0, 1.0)
        text_surface = self.font.render(text, True, (255, 255, 255))
        text_data = pygame.image.tostring(text_surface, "RGBA", True)
        texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, text_surface.get_width(), text_surface.get_height(),
                     0, GL_RGBA, GL_UNSIGNED_BYTE, text_data)
        glEnable(GL_TEXTURE_2D)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(x, y)
        glTexCoord2f(1, 0); glVertex2f(x + text_surface.get_width(), y)
        glTexCoord2f(1, 1); glVertex2f(x + text_surface.get_width(), y + text_surface.get_height())
        glTexCoord2f(0, 1); glVertex2f(x, y + text_surface.get_height())
        glEnd()
        glDisable(GL_TEXTURE_2D)
        glDeleteTextures(1, [texture])

    def draw_status_info(self):
        margin = 20
        padding = 10
        box_width = 220
        box_height = 90
        x = margin
        y = margin
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.width, self.height, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glDisable(GL_DEPTH_TEST)
        glColor4f(0.0, 0.0, 0.0, 0.7)
        glBegin(GL_QUADS)
        glVertex2f(x, y)
        glVertex2f(x + box_width, y)
        glVertex2f(x + box_width, y + box_height)
        glVertex2f(x, y + box_height)
        glEnd()
        glColor3f(0.7, 0.7, 0.7)
        glBegin(GL_LINE_LOOP)
        glVertex2f(x, y)
        glVertex2f(x + box_width, y)
        glVertex2f(x + box_width, y + box_height)
        glVertex2f(x, y + box_height)
        glEnd()
        self.render_text("Coordinate Range:", x + padding, y + padding)
        self.render_text("X, Z: -100 to 100", x + padding, y + padding + 30)
        self.render_text("Y: 0 to 100", x + padding, y + padding + 60)
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        glEnable(GL_DEPTH_TEST)

    def render(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        self.camera.apply_view()
        self.draw_grid()
        # Conditional rendering based on visibility flags
        if self.axes_visible:
            self.draw_axes(100.0)
        if self.labels_visible:
            self.draw_coordinate_labels()
        self.draw_status_info()
        self.draw_angle_display()

    def run(self):
        if not self.initialize():
            return
        while not glfw.window_should_close(self.window):
            self.render()
            glfw.swap_buffers(self.window)
            glfw.poll_events()
        pygame.quit()
        glfw.terminate()

if __name__ == "__main__":
    cad = CADPlatform()
    cad.run()