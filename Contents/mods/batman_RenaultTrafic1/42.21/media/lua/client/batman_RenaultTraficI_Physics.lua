-- Local physics calibration for this vehicle only. Do not change inventory items: their
-- identity, quality and wear remain vanilla, including when removed and installed elsewhere.
-- PZ 42.21 replaces effective part damping in updatePartStats, then uploads it every driving
-- frame. Reapply after that on OnTick and upload only when an effective coefficient changed.
-- Client/solo only: dedicated servers do not run this local driving-physics adjustment.

batman_RenaultTraficI = batman_RenaultTraficI or {}
local state = batman_RenaultTraficI

-- Vanilla NormalSuspension2 / ModernSuspension2, matching mechanicType = 2.
local BASE_DAMPING = 3.88
local BASE_COMPRESSION = 4.83
local PART_IDS = {
    "SuspensionFrontLeft", "SuspensionFrontRight",
    "SuspensionRearLeft", "SuspensionRearRight",
}
local lastVehicleByPlayer = {}
local lastTiltBandByPlayer = {}

function state.ApplySuspensionCalibration(vehicle)
    local script = vehicle:getScript()
    local dampingScale = script:getSuspensionDamping() / BASE_DAMPING
    local compressionScale = script:getSuspensionCompression() / BASE_COMPRESSION
    local changed = false
    for _, id in ipairs(PART_IDS) do
        local part = vehicle:getPartById(id)
        local item = part and part:getInventoryItem()
        if item then
            -- Recompute from the item, never from the previously scaled part value.
            -- Preserve the vanilla condition curve and minimum before scaling it.
            local condition = item:getCondition()
            local damping = VehiclePart.getNumberByCondition(
                item:getSuspensionDamping(), condition, 0.6) * dampingScale
            local compression = VehiclePart.getNumberByCondition(
                item:getSuspensionCompression(), condition, 0.6) * compressionScale
            if math.abs(part:getSuspensionDamping() - damping) > 0.001 then
                part:setSuspensionDamping(damping)
                changed = true
            end
            if math.abs(part:getSuspensionCompression() - compression) > 0.001 then
                part:setSuspensionCompression(compression)
                changed = true
            end
        end
    end
    if changed then
        vehicle:updateBulletStats()
    end
end

-- Remove the previous callback on Lua reload; functions cannot carry marker fields.
if state.PhysicsTick then
    Events.OnTick.Remove(state.PhysicsTick)
end

function state.PhysicsTick()
    for index = 0, getNumActivePlayers() - 1 do
        local player = getSpecificPlayer(index)
        local vehicle = player and player:getVehicle()
        if vehicle and vehicle:getDriver() == player
                and vehicle:getScriptName() == "Base.batman_RenaultTraficI" then
            state.ApplySuspensionCalibration(vehicle)
            if lastVehicleByPlayer[index] ~= vehicle then
                lastVehicleByPlayer[index] = vehicle
                lastTiltBandByPlayer[index] = nil
                local script = vehicle:getScript()
                print("[batman_RenaultTraficI] suspension calibration active: stiffness="
                    .. tostring(script:getSuspensionStiffness())
                    .. ", healthy damping=" .. tostring(script:getSuspensionDamping())
                    .. ", healthy compression=" .. tostring(script:getSuspensionCompression())
                    .. ", model offset y=" .. tostring(script:getModelOffset():y())
                    .. ", total mass=" .. tostring(vehicle:getMass()))
                for _, id in ipairs(PART_IDS) do
                    local part = vehicle:getPartById(id)
                    local item = part and part:getInventoryItem()
                    if item then
                        print("[batman_RenaultTraficI] " .. id
                            .. ": condition=" .. tostring(item:getCondition())
                            .. ", damping=" .. tostring(part:getSuspensionDamping())
                            .. ", compression=" .. tostring(part:getSuspensionCompression()))
                    end
                end
            end
            -- Record large actual chassis inclinations, once per new 5-degree band per incident.
            -- This measures orientation, not a collision, and does not alter physics.
            local upDot = math.max(-1, math.min(1, vehicle:getUpVectorDot()))
            local tilt = math.acos(upDot) * 180 / math.pi
            local band = math.floor(tilt / 5)
            if tilt < 5 then
                lastTiltBandByPlayer[index] = nil
            elseif tilt >= 15 and band > (lastTiltBandByPlayer[index] or 0) then
                lastTiltBandByPlayer[index] = band
                print("[batman_RenaultTraficI] chassis tilt=" .. tostring(math.floor(tilt))
                    .. " deg, speed=" .. tostring(vehicle:getCurrentAbsoluteSpeedKmHour()))
            end
        else
            lastVehicleByPlayer[index] = nil
            lastTiltBandByPlayer[index] = nil
        end
    end
end

Events.OnTick.Add(state.PhysicsTick)
