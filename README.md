# rgb_matrix_countdown


I used this [Youtube video](https://www.youtube.com/watch?v=2mq3ZBaSdN8) to flash circuitpython to a raspberry pi pico 2040 and set up the base functionality. They use [this github](https://github.com/yakaracolombia/MATRIXPORTAL_SPRITE_ANIMATIONS_PLAYER_RP2040/tree/main) to flash the base packages and functionality.

Notes:
- The github will flash the Spanish version of ciruitpython. This didn't bother me since I speak Spanish, but you may need google translate when debugging any error messages.
- I copied the same pinout as the diagram in the video and github, but I had to swap some of the colors in order to get the output to look correct. (I believe it was the blue and green pins). I also connected each of the 3 grounds to their own ground pin on the pico (though you could probably connect them all to the same ground pin).

Additional Setup:
- I added two buttons using the GP21 and GP22 pins. To do this, I added jumper cables to these pins on the pico, as well as used a breadboard to connect the buttons to the pico. 


For this project, I used the following hardware:
- A raspberry pi pico 2040 (I got this [starter kit](https://a.co/d/6FTeLZe))
- A breadboard, 2 buttons, and additional jumper cables (There are pleanty of starter kits that contain this).
- A 64x32 RGB LED matrix (I got this [one](https://a.co/d/2VY0FsE))
- A power adapter for the LED matrix (I got this [one](https://a.co/d/3frTXtB) and used the LED terminal connector with the power cables included in the LED matrix kit).
  
