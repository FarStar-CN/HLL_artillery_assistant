from dataclasses import dataclass

MIL_K_DEFAULT = 1500.0 / 356.0
MIL_BASE_DEFAULT = 1002.0


@dataclass(frozen=True)
class ArtilleryProfile:
    country: str
    mode: str  # "STD" or "SPG"

    mil_base: float = MIL_BASE_DEFAULT
    mil_k: float = MIL_K_DEFAULT

    min_distance: float = 100.0
    max_distance: float = 1600.0

    sector_angle: float = 15.0
    sector_radius: float = 1600.0

    move_speed_x: float = 10.0
    move_speed_y: float = 1.0
    tilt_speed: float = 5.0

    @property
    def label(self) -> str:
        return f"{self.country}_{self.mode}"

    def compute_mil(self, distance_m: float) -> float:
        return self.mil_base - distance_m / self.mil_k

    def compute_effective_distance(self, distance_m: float, delta_mil: float) -> float:
        return distance_m - self.mil_k * delta_mil


USA_STD = ArtilleryProfile(
    country="USA", mode="STD",
    mil_base=MIL_BASE_DEFAULT, mil_k=MIL_K_DEFAULT,
    min_distance=100.0, max_distance=1600.0,
    sector_angle=15.0, sector_radius=1600.0,
    move_speed_x=10.0, move_speed_y=1.0,
    tilt_speed=5.0,
)

USA_SPG = ArtilleryProfile(
    country="USA", mode="SPG",
    mil_base=MIL_BASE_DEFAULT, mil_k=MIL_K_DEFAULT,
    min_distance=100.0, max_distance=1000.0,
    sector_angle=180.0, sector_radius=1000.0,
    move_speed_x=10.0, move_speed_y=10.0,
    tilt_speed=5.0,
)

UK_STD = ArtilleryProfile(
    country="UK", mode="STD",
    mil_base=MIL_BASE_DEFAULT, mil_k=MIL_K_DEFAULT,
    min_distance=100.0, max_distance=1600.0,
    sector_angle=15.0, sector_radius=1600.0,
    move_speed_x=10.0, move_speed_y=1.0,
    tilt_speed=5.0,
)

UK_SPG = ArtilleryProfile(
    country="UK", mode="SPG",
    mil_base=MIL_BASE_DEFAULT, mil_k=MIL_K_DEFAULT,
    min_distance=100.0, max_distance=1600.0,
    sector_angle=15.0, sector_radius=1600.0,
    move_speed_x=10.0, move_speed_y=1.0,
    tilt_speed=5.0,
)

USSR_STD = ArtilleryProfile(
    country="USSR", mode="STD",
    mil_base=MIL_BASE_DEFAULT, mil_k=MIL_K_DEFAULT,
    min_distance=100.0, max_distance=1600.0,
    sector_angle=15.0, sector_radius=1600.0,
    move_speed_x=10.0, move_speed_y=1.0,
    tilt_speed=5.0,
)

USSR_SPG = ArtilleryProfile(
    country="USSR", mode="SPG",
    mil_base=MIL_BASE_DEFAULT, mil_k=MIL_K_DEFAULT,
    min_distance=100.0, max_distance=1600.0,
    sector_angle=15.0, sector_radius=1600.0,
    move_speed_x=10.0, move_speed_y=1.0,
    tilt_speed=5.0,
)

DE_STD = ArtilleryProfile(
    country="DE", mode="STD",
    mil_base=MIL_BASE_DEFAULT, mil_k=MIL_K_DEFAULT,
    min_distance=100.0, max_distance=1600.0,
    sector_angle=15.0, sector_radius=1600.0,
    move_speed_x=10.0, move_speed_y=1.0,
    tilt_speed=5.0,
)

DE_SPG = ArtilleryProfile(
    country="DE", mode="SPG",
    mil_base=MIL_BASE_DEFAULT, mil_k=MIL_K_DEFAULT,
    min_distance=100.0, max_distance=1600.0,
    sector_angle=15.0, sector_radius=1600.0,
    move_speed_x=10.0, move_speed_y=1.0,
    tilt_speed=5.0,
)

PROFILES = {
    "USA_STD": USA_STD,
    "USA_SPG": USA_SPG,
    "UK_STD": UK_STD,
    "UK_SPG": UK_SPG,
    "USSR_STD": USSR_STD,
    "USSR_SPG": USSR_SPG,
    "DE_STD": DE_STD,
    "DE_SPG": DE_SPG,
}

COUNTRIES = ("USA", "UK", "USSR", "DE")
DEFAULT_COUNTRY = "USA"


def get_profile(country: str, mode: str) -> ArtilleryProfile:
    return PROFILES[f"{country}_{mode}"]


def get_default_profile() -> ArtilleryProfile:
    return USA_STD
