from abc import ABC, abstractmethod
import geopandas as gpd


class NotificationBackend(ABC):
    @abstractmethod
    def notify(self, affected_areas: gpd.GeoDataFrame) -> None:
        pass


class ConsoleNotificationBackend(NotificationBackend):
    def notify(self, affected_areas: gpd.GeoDataFrame) -> None:
        if affected_areas.empty:
            print("No affected areas found.")
            return

        print(f"Affected areas ({len(affected_areas)}):")
        # Currently printed at gadm level 3.
        sorted_areas = affected_areas.sort_values(by="NAME_3")
        for row in sorted_areas.itertuples():
            print(f"- {row.NAME_3}, GID: {row.GID_3}")
