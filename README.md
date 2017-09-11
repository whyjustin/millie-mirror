# Millie Mirror

## Installation

### OpenCV

Install OpenCV and dependencies on the Raspberry Pi. Follow the following tutorial. For my setup, however, I used the 
lite version of Raspbian Stretch since I ran out of room on the standard version (8GB SD).

http://www.pyimagesearch.com/2016/04/18/install-guide-raspberry-pi-3-raspbian-jessie-opencv-3/

Next configure the Raspberry Pi camera and the Python modules to access it. Again, following a tutorial.
 
http://www.pyimagesearch.com/2015/03/30/accessing-the-raspberry-pi-camera-with-opencv-and-python/

### GTK and PyGObject

```
sudo apt-get install python-gtk2
```

### PiCamera

```
sudo apt-get install python-picamera
```

### Disable Overscan

```
sudo raspi-config
```

Under Advanced Options, select Overscan and disable. Reboot.

### Setup X Server for Lite Installation

Since I used a lite version of Raspbian, I needed to configure an X Server to handle the GUI.

#### X Server

First install XOrg and xinit.

```
sudo apt-get install xserver-xorg
sudo apt-get install xinit

```

Next configure .xinitrc to boot the Python script upon start. Create a file ~/.xinitrc with the following contents.

```
#!/usr/bin/env bash

exec python /home/pi/millie-mirror/application.py
```

#### Configure Default Height and Width

Since there is no window manager, force GTK to a default size rather than relying on fullscreen. This can be done by 
adding a `settings.json` file to the source code directory.

```
{
    "default_width": 1900,
    "default_height": 1080
}
```

## Configuration

### Facial Training

+ Start the mirror
    ```
    python application.py
    ```
+ Display the camera by typing `v`
+ Adjust the camera display to approximately match the mirror reflection using `-`, `+`, and the directional arrows
+ Display the face box by typing `f`

You should now see the camera displayed on the screen with a white rectangle around any face. There should be a `-1`
next to each face indicating that it is not recognized. Next, train the faces.

+ Begin training by typing `a`
+ With a single person identified by rectangle, take a picture using `Enter`
+ Continue to take many pictures with various expressions and angles of the face using `Enter`
+ After capturing the training pictures, type `a` and wait for the data to process
+ The person trained should now appear with a `1` next to their rectangle
 
Continue this process with any users you would like to train for the mirror. 

### Scenes

Scenes are configured in the `./scenes/default.json` file. The file takes an array of scenes. Below is an example
`default.json` file.

```
[
    {
        "actors": [
          {
            "users": [-1],
            "loop": [
              { "top": -150, "left": -150 },
              { "top": -175, "left": -175 },
              { "top": -200, "left": -200 },
              { "top": -200, "left": -225 },
              { "top": -175, "left": -225 },
              { "top": -150, "left": -200 },
              { "top": -150, "left": -175 }
            ],
            "source": "images/bluebird.gif"
          },
          {
            "loop": [
              { "bottom": "100%", "left": 0 }
            ],
            "source": "images/background.gif"
          }
        ],
        "triggers": [
          {
            "target": 1,
            "users": [-1],
            "box": {
              "top": 0,
              "left": 0,
              "bottom": "100%",
              "right": "40%"
            }
          }
        ]
    }
]
```

#### Actors

An actor is an image that can be displayed on the mirror. Actors contain:

+ `users` (optional): an array of users referenced by their training number. -1 can be used for unknown users.
+ `loop`: an array of positions where the image should be displayed. If the users array is specified, these numbers
 are relative to the user's face, if no user specified these numbers are absolute. Percentage and absolute numbers
 are valid.
+ `source`: the source of the image. gif are acceptable for animations.

#### Triggers

A trigger allows specification as to when to show the scene. This allows for multiple scenes which are added or removed
dependent on their triggers. Triggers are optional.

+ `target`: Which scene to show when trigger is activated. Scenes are referenced by their position in the scene's array.
+ `users`: Which actors can activate the trigger
+ `box`: The bounding box which will cause the trigger

In other words, when the user's face appears within the box, the scene will switch the the target.
