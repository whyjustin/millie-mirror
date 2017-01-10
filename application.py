import threading
import time

import cv2
import gobject
import gtk
import numpy

import face_recognizer
import settings
import webcam

gobject.threads_init()


class MillieMirror:
    def __init__(self):
        self.settings_marshaller = settings.SettingsMarshaller()
        self.settings = self.settings_marshaller.settings
        self.face_recognizer = face_recognizer.FaceRecognizer()

        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.connect("destroy", gtk.main_quit)
        self.window.connect("key_press_event", self.on_key_press_event)
        self.window.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(0, 0, 0))

        self.gtk_fixed = gtk.Fixed()

        self.gtk_image = gtk.Image()
        self.event_box_image = gtk.EventBox()
        self.event_box_image.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(0, 0, 0))
        self.event_box_image.add(self.gtk_image)
        self.gtk_fixed.add(self.event_box_image)

        self.info_text = gtk.TextView()
        self.info_text.set_editable(False)
        self.info_text.set_cursor_visible(False)
        self.text_buffer = gtk.TextBuffer()
        self.info_text.set_buffer(self.text_buffer)
        self.event_box_info_text = gtk.EventBox()
        self.event_box_info_text.add(self.info_text)
        self.gtk_fixed.add(self.event_box_info_text)

        self.window.add(self.gtk_fixed)
        self.window.fullscreen()
        self.gtk_fixed.show()
        self.window.show()
        self.screen_width, self.screen_height = self.window.get_size()

        self.gtk_drawing_area = gtk.DrawingArea()
        self.gtk_drawing_area.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(0, 0, 0))
        self.gtk_drawing_area.connect("expose_event", self.expose_event)
        self.gtk_drawing_area.connect("configure_event", self.configure_event)
        self.gtk_drawing_area.set_size_request(self.screen_width, self.screen_height)
        self.pixmap = None
        self.gtk_fixed.add(self.gtk_drawing_area)
        self.gtk_drawing_area.show()

        self.settings_marshaller.default_if_none('background_image_width', self.screen_width)
        self.settings_marshaller.default_if_none('background_image_height', self.screen_height)
        self.settings_marshaller.default_if_none('left_pad', 0)
        self.settings_marshaller.default_if_none('top_pad', 0)
        self.settings_marshaller.default_if_none('showing_background_image', False)
        self.settings_marshaller.default_if_none('showing_face_rectangles', False)
        self.settings_marshaller.default_if_none('recognition_threshold', 80)
        self.settings_marshaller.save()

        self.face_recognizer.update_threshold(self.settings.recognition_threshold)

        self.camera = webcam.OpenCVCapture(device_id=0)

        self.background_thread = threading.Thread(target=self.background_work)
        self.background_thread.daemon = True
        self.kill_background = False

    def main(self):
        self.background_thread.start()
        gtk.main()

    def background_work(self):
        while True and not self.kill_background:
            x = (self.screen_width - self.settings.background_image_width) / 2
            y = (self.screen_height - self.settings.background_image_height) / 2
            x += self.settings.left_pad
            y += self.settings.top_pad

            background_image = numpy.copy(self.camera.read())
            height, width, z = background_image.shape
            scale_width = float(self.settings.background_image_width) / width
            scale_height = float(self.settings.background_image_height) / height

            # width = self.screen_width if self.settings.background_image_width > self.screen_width else self.settings.background_image_width
            # height = self.screen_height if self.settings.background_image_height > self.screen_height else self.settings.background_image_height

            background_image = cv2.flip(background_image, 1)
            recognition_image = numpy.copy(background_image)
            faces = self.face_recognizer.detect_faces(recognition_image)

            background_image = cv2.resize(background_image,
                                          (self.settings.background_image_width, self.settings.background_image_height))


            # image_cv = cv2.cv.fromarray(background_image)
            #
            # image_final = numpy.asarray(image_cv)


            background_image = background_image[..., ::-1]

            gobject.idle_add(self.foreground_work, (x, y, scale_width, scale_height), background_image, faces)

            if not self.kill_background:
                time.sleep(1.0 / 30)

    def on_key_press_event(self, widget, event):
        if event.keyval == gtk.keysyms.Escape:
            self.kill_background = True
            gtk.main_quit()
        elif event.keyval == gtk.keysyms.v:
            self.settings.showing_background_image = not self.settings.showing_background_image
        elif event.keyval == gtk.keysyms.plus:
            delta_x, delta_y = self.calculate_image_scale()
            self.settings.background_image_width += delta_x
            self.settings.background_image_height += delta_y
        elif event.keyval == gtk.keysyms.minus:
            delta_x, delta_y = self.calculate_image_scale()
            if self.settings.background_image_width - delta_x > 0 and self.settings.background_image_height - delta_y > 0:
                self.settings.background_image_width -= delta_x
                self.settings.background_image_height -= delta_y
        elif event.keyval == gtk.keysyms.Up:
            self.settings.top_pad -= 10
        elif event.keyval == gtk.keysyms.Down:
            self.settings.top_pad += 10
        elif event.keyval == gtk.keysyms.Left:
            self.settings.left_pad -= 10
        elif event.keyval == gtk.keysyms.Right:
            self.settings.left_pad += 10
        elif event.keyval == gtk.keysyms.greater:
            self.settings.recognition_threshold += 20
            self.face_recognizer.update_threshold(self.settings.recognition_threshold)
        elif event.keyval == gtk.keysyms.less:
            self.settings.recognition_threshold -= 20
            self.face_recognizer.update_threshold(self.settings.recognition_threshold)
        elif event.keyval == gtk.keysyms.f:
            self.settings.showing_face_rectangles = not self.settings.showing_face_rectangles

        self.settings_marshaller.save()

    def calculate_image_scale(self):
        return int(self.screen_width / 100), int(self.screen_height / 100)

    def foreground_work(self, transform, background_image, faces):
        self.pixmap.draw_rectangle(self.window.get_style().black_gc, gtk.TRUE, 0, 0, self.screen_width,
                                   self.screen_height)

        self.draw_background_image(transform, background_image)
        self.draw_face_rectangles(transform, faces)

        self.gtk_drawing_area.queue_draw_area(0, 0, self.screen_width, self.screen_height)

    def configure_event(self, widget, event):
        x, y, width, height = widget.get_allocation()
        self.pixmap = gtk.gdk.Pixmap(widget.window, width, height)

    def expose_event(self, widget, event):
        if self.pixmap is not None:
            x, y, width, height = event.area
            graphics_context = widget.window.new_gc()
            widget.window.draw_drawable(graphics_context, self.pixmap, x, y, x, y, width, height)

    def draw_background_image(self, transform, background_image):
        if self.settings.showing_background_image:
            x, y, scale_width, scale_height = transform
            img_pixbuf = gtk.gdk.pixbuf_new_from_array(background_image, gtk.gdk.COLORSPACE_RGB, 8)
            graphics_context = self.gtk_drawing_area.window.new_gc()
            self.pixmap.draw_pixbuf(graphics_context, img_pixbuf, 0, 0, x, y, -1, -1, gtk.gdk.RGB_DITHER_NONE, 0, 0)

            # self.gtk_image.set_from_pixbuf(img_pixbuf)
            # self.gtk_image.set_size_request(width, height)
            # self.gtk_image.show()
            # self.event_box_image.show()
            # self.gtk_fixed.move(self.event_box_image, x, y)
            # else:
            #     self.gtk_image.hide()
            #     self.event_box_image.hide()

    def draw_face_rectangles(self, transform, faces):
        if self.settings.showing_face_rectangles:
            x, y, scale_width, scale_height = transform
            for face in faces:
                self.pixmap.draw_rectangle(self.window.get_style().white_gc, gtk.FALSE, int(face.x * scale_width) + x,
                                           int(face.y * scale_height) + y, int(face.w * scale_width),
                                           int(face.h * scale_height))


if __name__ == "__main__":
    try:
        application = MillieMirror()
        application.main()
    except KeyboardInterrupt:
        pass
