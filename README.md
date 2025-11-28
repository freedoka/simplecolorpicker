# simplecolorpicker
A simple color picker tool. Simply activate and pick any colors from the screen.

Sometimes I needed to get some color from the screen. I used to screenshot the screen, load my graphics editing software and then pick the color. This started to be very annoying when I need to work with a lot of images and I needed to color match them. 

How it works: simply activate it and you will see a tooltip next to your mouse with the color you are on in that moment. Click it and the color is coppied to the clipboard. 

Grab the python code and use it directly like that or if you want to make an exe out of it then simply do the following:

1. Install PyInstaller (if you don’t have it):
   pip install pyinstaller

2. Open a terminal in the folder where you saved the script, then run:
   pyinstaller --onefile --noconsole simplecolorpicker.py

3. For convenience you can compile with the icon I added here (or use your own):
   pyinstaller --onefile --noconsole --icon=simplecolorpickericon.ico simplecolorpicker.py

If you like this leave a comment here. 
