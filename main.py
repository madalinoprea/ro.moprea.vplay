import mc
from vplay import Vplay

mc.LogInfo('Init VPLAY')
v = Vplay()

mc.ActivateWindow(14000)
if v.toggle_login():
    pass
else:
    mc.ShowDialogOk('Vplay', 'Unable to connect with provided credentials')