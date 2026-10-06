-- Vanilla selects TruckBed automatically only for TrunkDoor/DoorRear openings.
-- Give this van's sliding cargo door the same loot-panel behaviour.
require "Vehicles/TimedActions/ISOpenVehicleDoor"

batman_RenaultTraficI = batman_RenaultTraficI or {}
batman_RenaultTraficI.CargoUI = batman_RenaultTraficI.CargoUI or {}
local state = batman_RenaultTraficI.CargoUI

if not state.installed then
    local previous = ISOpenVehicleDoor.selectContainerInLootWindow

    function ISOpenVehicleDoor:selectContainerInLootWindow()
        if self.vehicle and self.part and self.character
                and self.vehicle:getScriptName() == "Base.batman_RenaultTraficI"
                and self.part:getId() == "DoorRearRight"
                and not self.character:getVehicle() then
            local cargo = self.vehicle:getPartById("TruckBed")
            local playerNum = self.character:getPlayerNum()
            local loot = getPlayerLoot(playerNum)
            if cargo and cargo:getItemContainer() and loot
                    and self.vehicle:canAccessContainer(cargo:getIndex(), self.character) then
                loot:setForceSelectedContainer(cargo:getItemContainer(), 100)
                loot:setVisible(true)
                local joypadData = getJoypadData(playerNum)
                if joypadData then
                    joypadData.focus = loot
                    updateJoypadFocus(joypadData)
                    self.character:setBannedAttacking(true)
                else
                    loot.collapseCounter = 0
                    if loot.isCollapsed then
                        loot.isCollapsed = false
                        loot:clearMaxDrawHeight()
                        loot.collapseCounter = -30
                    end
                end
            end
        end
        return previous(self)
    end

    state.installed = true
end
