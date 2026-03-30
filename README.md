********************************************************************************************************
*███████╗██╗      █████╗ ███╗   ███╗███████╗██╗    ██╗ █████╗ ████████╗ ██████╗██╗  ██╗███████╗██████╗ *
*██╔════╝██║     ██╔══██╗████╗ ████║██╔════╝██║    ██║██╔══██╗╚══██╔══╝██╔════╝██║  ██║██╔════╝██╔══██╗*
*█████╗  ██║     ███████║██╔████╔██║█████╗  ██║ █╗ ██║███████║   ██║   ██║     ███████║█████╗  ██████╔╝*
*██╔══╝  ██║     ██╔══██║██║╚██╔╝██║██╔══╝  ██║███╗██║██╔══██║   ██║   ██║     ██╔══██║██╔══╝  ██╔══██╗*
*██║     ███████╗██║  ██║██║ ╚═╝ ██║███████╗╚███╔███╔╝██║  ██║   ██║   ╚██████╗██║  ██║███████╗██║  ██║*
*╚═╝     ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝ ╚══╝╚══╝ ╚═╝  ╚═╝   ╚═╝    ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝*
********************************************************************************************************

Welcome to FlameWatcher, a short, pretty basic bit of python code designed to track bright objects. Obvious disclaimer to never leave 
a flame unattended- this is designed to allow you to focus on other tasks while in the same room, rather than devoting your sole 
attention to the bright object. This is especially helpful for candles with long burn times, which I'll use as the example henceforth.

Getting Started
----------------

You'll need a video camera (a webcam works fine and can awork directly with openCV rather than via harvesters) to get started.

To get the code working, you'll need to read the Harvesters documentation (https://github.com/genicam/harvesters) and know where your 
CTI file is. Additionally, adjust the threshold value depending on your camera. For the interested reader, this value depends on your
camera's resolution, its aperture (f-stop) and its ISO. When adjusting, it is helpful to note that underexposure is more
favourable than overexposure. If you can't adjust the camera to be perfectly exposed when pointed at the flame, aim for slight 
underexposure. The default value for the threshold is 0.08.

Additional Features
--------------------

Included is a crop function- this can help performance on lower end machines to achieve a higher output framerate. Do make sure
the expected position of the base of your flame remains inside the crop at all times.

Also included is a "response function" - this is helpful for getting cool shots of the flame up close while still being able to track
it the whole way down. For the more generic case of a bright object, I imagine this would be helpful if the object is small.

Disclaimers
------------
I accept no liability for damages cause by use of this code/script, whether by itself or as integrated into a larger program. While 
I have, to the best of my ability, attempted to make the code as safe as possible, I cannot account for all outcomes. Do not use in 
safety-critical procedures. Do not leave any flame or flammable objects unattended. Always adhere to your organisation's risk 
assessment procedure when utilising this code.

Enjoy :)
