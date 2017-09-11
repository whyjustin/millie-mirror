import json
import os

import gtk


class Scene:
    def __init__(self):
        default_scene_file_name = 'scenes/default.json'

        self.scenes = None
        self.scene = None
        if os.path.isfile(default_scene_file_name):
            with open(default_scene_file_name, 'r') as scene_file:
                self.scenes = json.load(scene_file)

        self.next_scene = 0
        if self.scenes is not None and len(self.scenes) > 0:
            self.load_scene(self.next_scene)

    def load_scene(self, index):
        self.scene = self.scenes[index]

        if 'actors' in self.scene:
            for actor in self.scene['actors']:
                if 'enter' in actor:
                    actor['state'] = 'enter'
                else:
                    actor['state'] = 'loop'
                actor['frame_index'] = 0
                actor['is_exited'] = False

                if 'pixbuf_iter' not in actor:
                    actor['pixbuf_iter'] = gtk.gdk.PixbufAnimation(actor['source']).get_iter()
                actor['pixbuf_iter'].advance(0.0)

    def draw_frame(self, drawing_area, pixmap, transform, faces):
        if self.scene is None:
            return

        graphics_context = drawing_area.window.new_gc()
        all_actors_exited = True

        if 'actors' in self.scene:
            for actor in self.scene['actors']:
                if actor['is_exited']:
                    continue

                all_actors_exited = False
                pixbuf = actor['pixbuf_iter'].get_pixbuf()
                frame = actor[actor['state']][actor['frame_index']]

                if 'users' in actor:
                    for face in faces:
                        if int(face.user) not in actor['users']:
                            return

                        left, top = self.calculate_position(drawing_area, pixbuf, transform, frame, face)
                        pixmap.draw_pixbuf(graphics_context, pixbuf, 0, 0, left, top)
                else:
                    left, top = self.calculate_position(drawing_area, pixbuf, transform, frame)
                    pixmap.draw_pixbuf(graphics_context, pixbuf, 0, 0, left, top)

                actor['frame_index'] += 1
                if actor['frame_index'] >= len(actor[actor['state']]):
                    if actor['state'] == 'enter':
                        actor['state'] = 'loop'
                    elif actor['state'] == 'exit':
                        actor['is_exited'] = True

                    actor['frame_index'] = 0

                actor['pixbuf_iter'].advance()

        self.handle_triggers(drawing_area, transform, faces)
        if all_actors_exited:
            self.load_scene(self.next_scene)

    def handle_triggers(self, drawing_area, transform, faces):
        if 'triggers' not in self.scene:
            return

        for trigger in self.scene['triggers']:
            box = self.normalize_position(drawing_area, trigger['box'])
            for face in faces:
                if int(face.user) not in trigger['users']:
                    return

                face_position = self.normalize_face_position(transform, face)
                if box.left < face_position.left and box.right > face_position.right and box.top < face_position.top and box.bottom > face_position.bottom:
                    self.next_scene = trigger['target']
                    for actor in self.scene['actors']:
                        if 'exit' in actor:
                            actor['state'] = 'exit'
                            actor['frame_index'] = 0
                        else:
                            actor['is_exited'] = True
                    return

    def calculate_position(self, drawing_area, pixbuf, transform, frame, face=None):
        position = self.normalize_position(drawing_area, frame)

        if face is not None:
            face_position = self.normalize_face_position(transform, face)
            if position.left is not None:
                left = face_position.left + position.left
            else:
                left = face_position.left + position.right - pixbuf.props.width

            if position.top is not None:
                top = face_position.top + position.top
            else:
                top = face_position.top + position.bottom - pixbuf.props.height
        else:
            if position.left is not None:
                left = position.left
            else:
                left = position.right - pixbuf.props.width

            if position.top is not None:
                top = position.top
            else:
                top = position.bottom - pixbuf.props.height

        return left, top

    @staticmethod
    def normalize_face_position(transform, face):
        x, y, scale_width, scale_height = transform
        position = Box()
        position.left = int(face.x * scale_width) + x
        position.right = int(face.x * scale_width) + x + face.w
        position.top = int(face.y * scale_height) + y
        position.bottom = int(face.y * scale_height) + y + face.h
        return position

    @staticmethod
    def normalize_position(drawing_area, box):
        position = Box()

        def extract_percentage(val):
            if str(val).endswith('%'):
                return True, int(val[:-1])
            else:
                return False, int(val)

        for horizontal_property in ['left', 'right']:
            if horizontal_property in box:
                is_percentage, value = extract_percentage(box[horizontal_property])
                if is_percentage:
                    setattr(position, horizontal_property, int(float(value) / 100 * drawing_area.allocation.width))
                else:
                    setattr(position, horizontal_property, value)

        for vertical_property in ['top', 'bottom']:
            if vertical_property in box:
                is_percentage, value = extract_percentage(box[vertical_property])
                if is_percentage:
                    setattr(position, vertical_property, int(float(value) / 100 * drawing_area.allocation.height))
                else:
                    setattr(position, vertical_property, value)

        return position


class Box:
    left = None
    top = None
    right = None
    bottom = None
