-- Renault Trafic I paint: the van was sold white (mostly) or blue, never in the random vanilla
-- palette (black, red, grey...). The vanilla colour is drawn by BaseVehicle.setScript before the
-- parts exist; a part "create" hook runs once, on the authority (solo or server), when the vehicle
-- is created (VehicleParts.createParts), so it can replace that colour for good: the colour is
-- saved with the vehicle and sent to the clients.
-- Hue / saturation / value ranges follow the vanilla white and blue of BaseVehicle.doVehicleColor.

batman_RenaultTraficI = batman_RenaultTraficI or {}

local WHITE_CHANCE = 70 -- percent; the rest is blue

-- GloveBox create hook (vehicle script, part GloveBox, lua block): keeps the vanilla behaviour of
-- the GloveBox template (Vehicles.Create.Default) and paints the van.
function batman_RenaultTraficI.CreateGloveBox(vehicle, part)
    Vehicles.Create.Default(vehicle, part)
    if ZombRand(100) < WHITE_CHANCE then
        vehicle:setColorHSV(0.15, ZombRandFloat(0.0, 0.08), ZombRandFloat(0.72, 0.80))
    else
        vehicle:setColorHSV(ZombRandFloat(0.57, 0.61), ZombRandFloat(0.85, 1.0), ZombRandFloat(0.62, 0.72))
    end
    vehicle:transmitColorHSV()
end
