-- Renault Trafic I: spawn zones, next to the vanilla Van (VehicleZoneDefinition.lua).
-- Lower chances than the Van: a European van is a rare sight in Kentucky.
require "VehicleZoneDefinition"

local ID = "Base.batman_RenaultTraficI"
local ZONES = { parkingstall = 2, medium = 2, junkyard = 2, bad = 1, trades = 6, delivery = 6 }

for zone, chance in pairs(ZONES) do
    local z = VehicleZoneDistribution and VehicleZoneDistribution[zone]
    if z and z.vehicles then
        z.vehicles[ID] = { index = -1, spawnChance = chance }
    end
end
