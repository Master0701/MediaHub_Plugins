# For backwards compatibility, importing the PIL drawers here.
try:
    from .pil import (
        CircleModuleDrawer,  # noqa: F401
        GappedSquareModuleDrawer,  # noqa: F401
        HorizontalBarsDrawer,  # noqa: F401
        RoundedModuleDrawer,  # noqa: F401
        SquareModuleDrawer,  # noqa: F401
        VerticalBarsDrawer,  # noqa: F401
    )
except ImportError:
    pass
