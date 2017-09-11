import threading
import time

import cv2
import gobject
import gtk
import numpy
import pango

import face_recognizer
import scene
import settings

gobject.threads_init()


class MillieMirror:
    def __init__(self):
        self.settings_marshaller = settings.SettingsMarshaller()
        self.settings = self.settings_marshaller.settings
        self.face_recognizer = face_recognizer.FaceRecognizer(self.settings)

        self.gtk_window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.gtk_window.connect("destroy", gtk.main_quit)
        self.gtk_window.connect("key_press_event", self.on_key_press_event)
        self.gtk_window.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(0, 0, 0))

        self.gtk_fixed = gtk.Fixed()
        self.gtk_window.add(self.gtk_fixed)

        if self.settings.default_height is not None and self.settings.default_width is not None:
            self.gtk_window.set_default_size(self.settings.default_width, self.settings.default_height)
        self.gtk_window.fullscreen()

        self.gtk_fixed.show()
        self.gtk_window.show()
        self.screen_width, self.screen_height = self.gtk_window.get_size()

        self.gtk_drawing_area = gtk.DrawingArea()
        self.gtk_drawing_area.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(0, 0, 0))
        self.gtk_drawing_area.connect("expose_event", self.expose_event)
        self.gtk_drawing_area.connect("configure_event", self.configure_event)
        self.gtk_drawing_area.set_size_request(self.screen_width, self.screen_height)
        self.gtk_pixmap = None
        self.gtk_fixed.add(self.gtk_drawing_area)
        self.gtk_drawing_area.show()

        #self.pixbuf_animation_blue_bird_iter = gtk.gdk.PixbufAnimation('images/bluebird.gif').get_iter()
        self.scene = scene.Scene()

        self.settings_marshaller.default_if_none('background_image_width', self.screen_width)
        self.settings_marshaller.default_if_none('background_image_height', self.screen_height)
        self.settings_marshaller.default_if_none('left_pad', 0)
        self.settings_marshaller.default_if_none('top_pad', 0)
        self.settings_marshaller.default_if_none('showing_background_image', False)
        self.settings_marshaller.default_if_none('showing_face_rectangles', False)
        self.settings_marshaller.default_if_none('recognition_threshold', 80)
        self.settings_marshaller.save()

        self.camera = self.get_camera()

        self.background_thread = threading.Thread(target=self.background_work)
        self.background_thread.daemon = True
        self.kill_background = False

        self.recognizing_face = False
        self.pending_delete_training = False
        self.temporary_notice_timer = None
        self.temporary_notice = None

    def main(self):
        self.background_thread.start()
        gtk.main()

    def get_camera(self):
        if self.settings.use_webcam:
            import webcam
            return webcam.OpenCVCapture(device_id=0)
        else:
            import picam
            return picam.OpenCVCapture()

    def background_work(self):
        time.sleep(2)
        while True and not self.kill_background:
            x = (self.screen_width - self.settings.background_image_width) / 2
            y = (self.screen_height - self.settings.background_image_height) / 2
            x += self.settings.left_pad
            y += self.settings.top_pad

            background_image = numpy.copy(self.camera.read())
            height, width, z = background_image.shape
            scale_width = float(self.settings.background_image_width) / width
            scale_height = float(self.settings.background_image_height) / height

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
                time.sleep(1.0 / 30.0)

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
            self.set_temporary_notice(
                "Threshold: " + str(self.settings.recognition_threshold) + ". Restart to take affect.")
        elif event.keyval == gtk.keysyms.less:
            self.settings.recognition_threshold -= 20
            self.set_temporary_notice(
                    "Threshold: " + str(self.settings.recognition_threshold) + ". Restart to take affect.")
        elif event.keyval == gtk.keysyms.f:
            self.settings.showing_face_rectangles = not self.settings.showing_face_rectangles
        elif event.keyval == gtk.keysyms.a:
            self.on_a_press()
        elif event.keyval == gtk.keysyms.r:
            self.on_r_press()
        elif event.keyval == gtk.keysyms.Return:
            self.on_enter_press()

        self.settings_marshaller.save()

    def calculate_image_scale(self):
        return int(self.screen_width / 100), int(self.screen_height / 100)

    def foreground_work(self, transform, background_image, faces):
        self.gtk_pixmap.draw_rectangle(self.gtk_window.get_style().black_gc, gtk.TRUE, 0, 0, self.screen_width,
                                       self.screen_height)

        self.draw_background_image(transform, background_image)
        self.draw_face_rectangles(transform, faces)
        self.scene.draw_frame(self.gtk_drawing_area, self.gtk_pixmap, transform, faces)

        self.draw_help_text()

        self.gtk_drawing_area.queue_draw_area(0, 0, self.screen_width, self.screen_height)

    def configure_event(self, widget, event):
        x, y, width, height = widget.get_allocation()
        self.gtk_pixmap = gtk.gdk.Pixmap(widget.window, width, height)

    def expose_event(self, widget, event):
        if self.gtk_pixmap is not None:
            x, y, width, height = event.area
            graphics_context = widget.window.new_gc()
            widget.window.draw_drawable(graphics_context, self.gtk_pixmap, x, y, x, y, width, height)

    def draw_background_image(self, transform, background_image):
        if self.settings.showing_background_image:
            x, y, scale_width, scale_height = transform
            img_pixbuf = gtk.gdk.pixbuf_new_from_array(background_image, gtk.gdk.COLORSPACE_RGB, 8)
            graphics_context = self.gtk_drawing_area.window.new_gc()
            self.gtk_pixmap.draw_pixbuf(graphics_context, img_pixbuf, 0, 0, x, y, -1, -1, gtk.gdk.RGB_DITHER_NONE, 0, 0)

    def draw_face_rectangles(self, transform, faces):
        if self.settings.showing_face_rectangles:
            x, y, scale_width, scale_height = transform
            white_gc = self.gtk_window.get_style().white_gc
            for face in faces:
                self.gtk_pixmap.draw_rectangle(white_gc, gtk.FALSE, int(face.x * scale_width) + x,
                                               int(face.y * scale_height) + y, int(face.w * scale_width),
                                               int(face.h * scale_height))
                pango_layout = self.gtk_drawing_area.create_pango_layout(face.user)
                font_description = pango.FontDescription("sans bold 36")
                pango_layout.set_font_description(font_description)
                text_pad = 2
                self.gtk_pixmap.draw_layout(white_gc, int(face.x * scale_width) + x + text_pad,
                                            int(face.y * scale_height) + y + text_pad, pango_layout)

    def draw_help_text(self):
        text = ""

        if self.recognizing_face:
            text = "Recognizing Face: Press Enter to capture. Press a to exit mode and train."
        elif self.pending_delete_training:
            text = "Delete all training data? Press Enter to continue. Press r to cancel."

        if self.temporary_notice is not None:
            text += "\n" + self.temporary_notice

        white_gc = self.gtk_window.get_style().white_gc
        pango_layout = self.gtk_drawing_area.create_pango_layout(text)
        font_description = pango.FontDescription("sans bold 36")
        pango_layout.set_font_description(font_description)
        text_pad = 2
        self.gtk_pixmap.draw_layout(white_gc, text_pad, text_pad, pango_layout)

    def on_a_press(self):
        if not self.pending_delete_training:
            if not self.recognizing_face:
                self.recognizing_face = True
                self.face_recognizer.init_new_face()
            else:
                self.recognizing_face = False
                self.face_recognizer.train_faces()

    def on_r_press(self):
        if not self.recognizing_face:
            self.pending_delete_training = not self.pending_delete_training

    def on_enter_press(self):
        if self.recognizing_face:
            image = numpy.copy(self.camera.read())
            image = cv2.flip(image, 1)
            success, error = self.face_recognizer.add_new_face(image)
            if not success:
                self.set_temporary_notice(error)
        if self.pending_delete_training:
            self.face_recognizer.delete_training()
            self.pending_delete_training = False

    def set_temporary_notice(self, text):
        if self.temporary_notice_timer is not None:
            self.temporary_notice_timer.cancel()

        self.temporary_notice = text

        def reset_notice():
            self.temporary_notice = None
            self.temporary_notice_timer = None

        self.temporary_notice_timer = threading.Timer(2.0, reset_notice)
        self.temporary_notice_timer.start()


if __name__ == "__main__":
    try:
        application = MillieMirror()
        application.main()
    except KeyboardInterrupt:
        pass
