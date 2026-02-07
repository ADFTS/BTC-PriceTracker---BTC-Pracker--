This is a small UI Based Program (1 to 1 Scale to Picture below) that displays the current live chart and price of Bitcoin.


Download Libraries:
Open Powershell, paste:
pip install tkinter matplotlib numpy requests pillow

Success!
->
Open Powershell in folder, paste:

Python "(Version).py"

Enter
-> BTC Pracker opens up.

-------------------------------
you'll need to create the exe yourself because of 25mb limitation on github:

Open Powershell, paste:
pip install pyinstaller
Success!
->
Open Powershell in folder

pyinstaller --onefile --windowed --icon=btc.ico --name="BTC Pracker" (Version).py

>> wait a min

>> succes

You can now find the .exe in the newly created "dist" folder.



-----------------------------------------
Original BTC Pracker 100k:

![Pracker](https://github.com/user-attachments/assets/9b5b7b4c-9bb3-4b2c-9c01-70da3409342d)

Old Versions (labels were mixed up):

<img width="640" height="966" alt="BTC-Pracker" src="https://github.com/user-attachments/assets/1434909a-c298-453f-a7a9-63e0b2715a52" />


Last Build (BTCPRefined.py) Now with Dollar, better optimisation and a Welcomescreen:
<img width="400" height="550" alt="options" src="https://github.com/user-attachments/assets/79a68598-92f8-44fe-b5c7-a333f26de6a7" />
<img width="644" height="453" alt="usd" src="https://github.com/user-attachments/assets/66f16d74-6218-42eb-9661-b196135c8094" />

-----------------------------------------
-----------------------------------------

known bugs:
-Theme applies not correctly automatically. Restart is needed.
-Big Dumps/Pumps will freeze Converter Value till restarted.
-Some temporary freezing while Dragging/Interacting with Window, Optimized Version will follow.
_________________________________________
Changelog:
[BTC-Pracker-HeikinAshi/Baseline] :
-> Cleaner Graph/Baseline
-> 2New added Converters.
-> 2New Realtime Trackers (USD/EUR, BTC/USD).
->12h AVG completly removed, no Text over F/G Index, no AVG-Line, only Graph is shown.

[BTC-Pracker-HeikinAshi/Baseline-AVG] :
-> Heikin Ashi Graph Added.
-> Cleaner Graph/Baseline.
-> 2New added Converters.
-> 2New Realtime Trackers (USD/EUR, BTC/USD).
-> 12h AVG got fixed, now showing correct AVG.
->AVG Price got moved besides Line
_________________________________________

BTC Profitpercentage:
Percenttracker for youre P/L, calculated of the cost of your AVG.
_________________________________________

BTCPWelcome:
Optimisation, Dollarprice in Options, a Welcomescreen while loading the Program at start.
_________________________________________

BTCPRefined:
-Fixed Loading Window from starting always in the middle of the screen, now starts where the X,Y coordinates are set from window_position.txt
-Fixed USD EUR price at the bottom, they are not any converter values any longer but instead directly received from API.

_________________________________________

Next Versions:
We'll see what comes to mind.

