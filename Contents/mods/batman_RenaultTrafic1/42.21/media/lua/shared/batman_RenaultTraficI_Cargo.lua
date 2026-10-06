-- One persistent TruckBed inventory with independent rear and side access.
-- The callback is used by BaseVehicle.canAccessContainer on solo/client/server.
require "Vehicles/Vehicles"

batman_RenaultTraficI = batman_RenaultTraficI or {}

function batman_RenaultTraficI.CargoAccess(vehicle, part, character)
    -- Preserve the existing rear-door and cab access rules.
    if Vehicles.ContainerAccess.TruckBedOpenInside(vehicle, part, character) then
        return true
    end
    if character:getVehicle() then return false end
    if math.floor(vehicle:getZ()) ~= math.floor(character:getZ()) then return false end

    local side = vehicle:getPartById("DoorRearRight")
    if not side or not side:getArea() then return false end
    if not vehicle:isInArea(side:getArea(), character) then return false end

    -- As with the vanilla rear door, a removed door leaves the opening usable.
    if not side:getInventoryItem() then return true end
    local door = side:getDoor()
    return door ~= nil and door:isOpen()
end
