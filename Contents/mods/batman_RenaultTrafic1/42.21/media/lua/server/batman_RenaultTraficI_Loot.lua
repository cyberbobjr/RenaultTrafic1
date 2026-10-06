-- Renault Trafic I: same cargo, glove box and seat loot as the vanilla Van.
-- ItemPickerJava.Parse() reads VehicleDistributions[1] after the distribution merge.
require "Vehicles/VehicleDistributions"

local function addTraficLoot()
    local d = VehicleDistributions and VehicleDistributions[1]
    if d and d.Van and not d.batman_RenaultTraficI then
        d.batman_RenaultTraficI = d.Van
    end
end

addTraficLoot()
Events.OnPostDistributionMerge.Add(addTraficLoot)
