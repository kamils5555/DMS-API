import threading
import random

class Desk:
    DEFAULT_SPEED_MMS = 32
    COLLISION_CHANCE = 0.05

    def __init__(self, desk_id, name, manufacturer, initial_position=680, min_position=680, max_position=1320):
        self.desk_id = desk_id
        self.config = {
            "name": name,
            "manufacturer": manufacturer,
        }
        self.state = {
            "position_mm": initial_position,
            "speed_mms": 0,
            "status": "Normal",
            "isPositionLost": False,
            "isOverloadProtectionUp": False,
            "isOverloadProtectionDown": False,
            "isAntiCollision": False,
        }
        self.usage = {
            "activationsCounter": 25,
            "sitStandCounter": 1,
        }
        self.lastErrors = [
            {"time_s": 120, "errorCode": 93},
        ]
        self.lock = threading.RLock()
        self.target_position_mm = initial_position
        self.min_position = min_position
        self.max_position = max_position
        self.sit_stand_position = (max_position - min_position) / 2 + min_position
        self.clock_s = 180
        self.collision_occurred = False

    def get_target_position(self):
        """Get the target position to move towards"""
        with self.lock:
            return self.target_position_mm

    def set_target_position(self, position_mm):
        """Set the target position to move towards, respecting min and max limits."""
        with self.lock:
            self.target_position_mm = max(self.min_position, min(position_mm, self.max_position))
            if position_mm != self.state["position_mm"]:
                self.usage["activationsCounter"] += 1

    def _generate_error(self):
        """Generate an error during movement."""
        with self.lock:
            self.lastErrors.insert(0, {"time_s": self.clock_s, "errorCode": 93})
            if len(self.lastErrors) > 10:
                self.lastErrors.pop()

            self.state["isAntiCollision"] = True
            self.state["status"] = "Collision"
            self.collision_occurred = True
    
    def update(self):
        """Update clock and position gradually toward target_position_mm within limits, increment sitStandCounter on crossing."""
        with self.lock:
            self.clock_s += 1

            successful_movement = False

            if self.collision_occurred:
                self.collision_occurred = False
                return

            previous_position = self.state["position_mm"]
            if self.state["position_mm"] < self.target_position_mm:
                self.state["position_mm"] += min(self.DEFAULT_SPEED_MMS, self.target_position_mm - self.state["position_mm"])
                self.state["position_mm"] = min(self.state["position_mm"], self.max_position)
                self.state["speed_mms"] = self.DEFAULT_SPEED_MMS
                successful_movement = True
            elif self.state["position_mm"] > self.target_position_mm:
                self.state["position_mm"] -= min(self.DEFAULT_SPEED_MMS, self.state["position_mm"] - self.target_position_mm)
                self.state["position_mm"] = max(self.state["position_mm"], self.min_position)
                self.state["speed_mms"] = -self.DEFAULT_SPEED_MMS
                successful_movement = True
            else:
                self.state["speed_mms"] = 0

            if (previous_position < self.sit_stand_position <= self.state["position_mm"]) or \
               (previous_position > self.sit_stand_position >= self.state["position_mm"]):
                self.usage["sitStandCounter"] += 1

            if successful_movement:
                if self.state["isAntiCollision"]:
                    self.state["isAntiCollision"] = False
                    self.state["status"] = "Normal"
                elif random.random() < self.COLLISION_CHANCE:
                    self._generate_error()
                    if self.state["speed_mms"] > 0:
                        self.state["position_mm"] = max(self.state["position_mm"] - 10, self.min_position)
                    elif self.state["speed_mms"] < 0:
                        self.state["position_mm"] = min(self.state["position_mm"] + 10, self.max_position)

                    self.target_position_mm = self.state["position_mm"]
                    self.state["speed_mms"] = 0

    def get_data(self):
        """Get a snapshot of the desk's data."""
        with self.lock:
            return {
                "config": self.config,
                "state": self.state,
                "usage": self.usage,
                "lastErrors": self.lastErrors,
            }

    def update_category(self, category, data):
        """Update a specific category of the desk."""
        with self.lock:
            if category == "state" and "position_mm" in data:
                self.set_target_position(data["position_mm"])
                return True

            return False
