%
O1000 (  )
( ------------------------------- )
( Muratec MW40 - Fanuc 31i        )
( PHASE D,usinage.1               )
( Auteur: toussain_g              )
( Vendredi 06.03.2026 - 07:53:04  )
( PP: 312_MuratecMW40_Fanuc31i_04 )
( ------------------------------- )
M9199 (init.)

M18
G28 W0
G28 U0 V0
M5

T3535 ( FRAISE D1.0 X 3 - XXX )
M108
( CONT CANAL2 FRONTALE - R+0 - L+0 )
M68 (ACTIVATION AXE C)
G28 H0
G28 G0 V0
M16 (FREIN BROCHE ON)
G97 M13 S15915
G0 Z4.
G0 X-7.2 Y0.2
G0 Z1.
G1 G98 Z-1. F200
G1 G41 X-7.6 Y0.7 F318
G3 X-9. Y0 I0 J-0.7    (R=0.7)
G1 Y-1.2
G3 X-7.4 Y-2. I0.8 J0    (R=0.8)
G1 X-4.6
G3 X-3. Y-1.2 I0 J0.8    (R=0.8)
G1 Y1.2
G3 X-4.6 Y2. I-0.8 J0    (R=0.8)
G1 X-7.4
G3 X-9. Y1.2 I0 J-0.8    (R=0.8)
G1 Y0
G3 X-7.6 Y-0.7 I0.7 J0    (R=0.7)
G1 G40 X-7.2 Y-0.2
G1 Z1. F1000
G0 Z4.
M109
G28 W0
G28 U0 V0

M18
M45
G97 M4 S2500

G4 X2
M59
G4 X2
M60
G4 X2
M15
M46

G28 U0 V0 W0
M69
M41
M230
M30
%
