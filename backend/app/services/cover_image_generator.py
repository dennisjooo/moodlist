"""Service for generating playlist cover images based on mood colors."""

import io
import base64
import structlog
from typing import Tuple, Literal
from PIL import Image, ImageDraw, ImageFilter

logger = structlog.get_logger(__name__)


class CoverImageGenerator:
    """Generates playlist cover images using triadic color schemes."""

    def __init__(self, size: int = 640):
        """Initialize the cover image generator.
        
        Args:
            size: Size of the square image in pixels (Spotify recommends 640x640)
        """
        self.size = size

    def generate_cover(
        self,
        primary_color: str,
        secondary_color: str,
        tertiary_color: str,
        style: Literal["diagonal", "radial", "mesh", "waves", "minimal"] = "diagonal"
    ) -> bytes:
        """Generate a cover image with the given color scheme.
        
        Args:
            primary_color: Primary hex color (e.g., "#FF5733")
            secondary_color: Secondary hex color
            tertiary_color: Tertiary hex color
            style: Visual style of the cover
            
        Returns:
            JPEG image as bytes
        """
        try:
            # Convert hex colors to RGB tuples
            colors = [
                self._hex_to_rgb(primary_color),
                self._hex_to_rgb(secondary_color),
                self._hex_to_rgb(tertiary_color)
            ]

            # Generate image based on style
            if style == "diagonal":
                image = self._generate_diagonal_gradient(colors)
            elif style == "radial":
                image = self._generate_radial_gradient(colors)
            elif style == "mesh":
                image = self._generate_mesh(colors)
            elif style == "waves":
                image = self._generate_waves(colors)
            elif style == "minimal":
                image = self._generate_minimal(colors)
            elif style == "modern":
                image = self._generate_modern_blend(colors)
            else:
                image = self._generate_diagonal_gradient(colors)

            # Apply subtle blur for smoothness
            image = image.filter(ImageFilter.GaussianBlur(radius=2))

            # Convert to JPEG bytes
            return self._image_to_jpeg_bytes(image)

        except Exception as e:
            logger.error(f"Failed to generate cover image: {str(e)}", exc_info=True)
            raise

    def generate_cover_base64(
        self,
        primary_color: str,
        secondary_color: str,
        tertiary_color: str,
        style: Literal["diagonal", "radial", "mesh", "waves", "minimal", "modern"] = "modern"
    ) -> str:
        """Generate a cover image and return it as base64 string for Spotify API.
        
        Args:
            primary_color: Primary hex color
            secondary_color: Secondary hex color
            tertiary_color: Tertiary hex color
            style: Visual style of the cover
            
        Returns:
            Base64-encoded JPEG string
        """
        jpeg_bytes = self.generate_cover(primary_color, secondary_color, tertiary_color, style)
        return base64.b64encode(jpeg_bytes).decode('utf-8')

    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple.
        
        Args:
            hex_color: Hex color string (e.g., "#FF5733")
            
        Returns:
            RGB tuple (r, g, b)
        """
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _interpolate_color(
        self,
        color1: Tuple[int, int, int],
        color2: Tuple[int, int, int],
        factor: float
    ) -> Tuple[int, int, int]:
        """Interpolate between two colors.
        
        Args:
            color1: First RGB color
            color2: Second RGB color
            factor: Interpolation factor (0-1)
            
        Returns:
            Interpolated RGB color
        """
        return tuple(int(color1[i] + (color2[i] - color1[i]) * factor) for i in range(3))

    def _generate_diagonal_gradient(self, colors: list) -> Image.Image:
        """Generate a smooth diagonal gradient with better color blending.
        
        Args:
            colors: List of three RGB tuples
            
        Returns:
            PIL Image
        """
        image = Image.new('RGB', (self.size, self.size))
        draw = ImageDraw.Draw(image)

        for y in range(self.size):
            for x in range(self.size):
                # Calculate position in diagonal (0-1) with smoother distribution
                factor = (x + y) / (2 * self.size)
                
                # Use smoother easing function for more natural transitions
                # Ease-in-out cubic for smoother color flow
                factor = self._ease_in_out_cubic(factor)
                
                # Better color distribution across all three colors
                if factor < 0.4:
                    # Primary to secondary transition (extended range)
                    local_factor = factor / 0.4
                    color = self._interpolate_color(colors[0], colors[1], local_factor)
                elif factor < 0.7:
                    # Secondary color dominant zone
                    local_factor = (factor - 0.4) / 0.3
                    color = self._interpolate_color(colors[1], colors[2], local_factor)
                else:
                    # Tertiary color with slight blend back to primary for harmony
                    local_factor = (factor - 0.7) / 0.3
                    # Blend between tertiary and a mix of tertiary + primary
                    blended = self._interpolate_color(colors[2], colors[0], 0.15)
                    color = self._interpolate_color(colors[2], blended, local_factor)
                
                draw.point((x, y), fill=color)

        return image
    
    def _ease_in_out_cubic(self, t: float) -> float:
        """Apply cubic easing for smoother transitions.
        
        Args:
            t: Input value (0-1)
            
        Returns:
            Eased value (0-1)
        """
        if t < 0.5:
            return 4 * t * t * t
        else:
            return 1 - pow(-2 * t + 2, 3) / 2

    def _generate_radial_gradient(self, colors: list) -> Image.Image:
        """Generate a smooth radial gradient from center with easing.
        
        Args:
            colors: List of three RGB tuples
            
        Returns:
            PIL Image
        """
        image = Image.new('RGB', (self.size, self.size))
        draw = ImageDraw.Draw(image)
        center = self.size / 2
        max_radius = center * 1.414  # Diagonal distance to corner

        for y in range(self.size):
            for x in range(self.size):
                # Calculate distance from center (0-1)
                distance = ((x - center) ** 2 + (y - center) ** 2) ** 0.5
                factor = min(distance / max_radius, 1.0)
                
                # Apply easing for smoother transitions
                factor = self._ease_in_out_cubic(factor)
                
                # Smoother color distribution
                if factor < 0.45:
                    local_factor = factor / 0.45
                    color = self._interpolate_color(colors[0], colors[1], local_factor)
                elif factor < 0.8:
                    local_factor = (factor - 0.45) / 0.35
                    color = self._interpolate_color(colors[1], colors[2], local_factor)
                else:
                    # Darken slightly at edges for depth
                    local_factor = (factor - 0.8) / 0.2
                    darkened = tuple(int(c * 0.85) for c in colors[2])
                    color = self._interpolate_color(colors[2], darkened, local_factor)
                
                draw.point((x, y), fill=color)

        return image

    def _generate_mesh(self, colors: list) -> Image.Image:
        """Generate a smooth mesh/blend of colors with modern gradient feel.
        
        Args:
            colors: List of three RGB tuples
            
        Returns:
            PIL Image
        """
        import math
        image = Image.new('RGB', (self.size, self.size))
        draw = ImageDraw.Draw(image)

        for y in range(self.size):
            for x in range(self.size):
                # Normalized position
                nx = x / self.size
                ny = y / self.size
                
                # Apply easing to both dimensions for smoother blending
                nx_eased = self._ease_in_out_cubic(nx)
                ny_eased = self._ease_in_out_cubic(ny)
                
                # Create flowing weights that blend more naturally
                # Use sine waves for organic feeling
                weight1 = (1 - nx_eased) * (1 - ny_eased * 0.7)  # Top-left (primary)
                weight2 = nx_eased * (1 - ny_eased * 0.7)  # Top-right (secondary)
                weight3 = ny_eased  # Bottom (tertiary) - stronger influence
                
                # Add subtle wave for visual interest
                wave = math.sin(nx * 3 + ny * 3) * 0.1
                weight1 += wave
                weight2 -= wave * 0.5
                weight3 += wave * 0.3
                
                # Normalize weights
                total = weight1 + weight2 + weight3
                if total > 0:
                    weight1 /= total
                    weight2 /= total
                    weight3 /= total
                
                # Calculate blended color
                color = tuple(
                    int(max(0, min(255, colors[0][i] * weight1 + colors[1][i] * weight2 + colors[2][i] * weight3)))
                    for i in range(3)
                )
                
                draw.point((x, y), fill=color)

        return image

    def _generate_waves(self, colors: list) -> Image.Image:
        """Generate wavy color bands.
        
        Args:
            colors: List of three RGB tuples
            
        Returns:
            PIL Image
        """
        import math
        
        image = Image.new('RGB', (self.size, self.size))
        draw = ImageDraw.Draw(image)

        for y in range(self.size):
            for x in range(self.size):
                # Create wave pattern
                wave = math.sin((x + y) * 0.01) * 0.5 + 0.5
                factor = (y / self.size + wave * 0.3) % 1.0
                
                # Transition through colors
                if factor < 0.33:
                    color = self._interpolate_color(colors[0], colors[1], factor * 3)
                elif factor < 0.66:
                    color = self._interpolate_color(colors[1], colors[2], (factor - 0.33) * 3)
                else:
                    color = self._interpolate_color(colors[2], colors[0], (factor - 0.66) * 3)
                
                draw.point((x, y), fill=color)

        return image

    def _generate_minimal(self, colors: list) -> Image.Image:
        """Generate a minimal design with color blocks.
        
        Args:
            colors: List of three RGB tuples
            
        Returns:
            PIL Image
        """
        image = Image.new('RGB', (self.size, self.size), colors[0])
        draw = ImageDraw.Draw(image)
        
        # Add geometric shapes with other colors
        # Large circle in bottom right
        circle_size = int(self.size * 0.7)
        draw.ellipse(
            [(self.size - circle_size, self.size - circle_size), (self.size + 100, self.size + 100)],
            fill=colors[1]
        )
        
        # Smaller circle in top left
        small_circle = int(self.size * 0.4)
        draw.ellipse(
            [(-100, -100), (small_circle, small_circle)],
            fill=colors[2]
        )

        return image

    def _generate_modern_blend(self, colors: list) -> Image.Image:
        """Generate a modern, smooth multi-directional blend like contemporary gradient tools.
        
        Creates a natural-looking gradient that flows from multiple directions
        with smooth color transitions, similar to popular gradient generators.
        
        Args:
            colors: List of three RGB tuples
            
        Returns:
            PIL Image
        """
        import math
        image = Image.new('RGB', (self.size, self.size))
        draw = ImageDraw.Draw(image)

        for y in range(self.size):
            for x in range(self.size):
                # Normalized coordinates
                nx = x / self.size
                ny = y / self.size
                
                # Apply easing
                nx_eased = self._ease_in_out_cubic(nx)
                ny_eased = self._ease_in_out_cubic(ny)
                
                # Create multiple gradient influences for rich blending
                # Diagonal from top-left to bottom-right
                diag1 = (nx_eased + ny_eased) / 2
                
                # Diagonal from top-right to bottom-left
                diag2 = ((1 - nx_eased) + ny_eased) / 2
                
                # Vertical influence
                vert = ny_eased
                
                # Horizontal influence
                horiz = nx_eased
                
                # Add subtle noise/variation for organic feel
                noise = (math.sin(nx * 10 + ny * 7) * math.cos(ny * 8 - nx * 6)) * 0.05
                
                # Combine influences with weights
                # This creates a complex, multi-directional flow
                factor1 = (diag1 * 0.4 + vert * 0.3 + noise)
                factor2 = (diag2 * 0.3 + horiz * 0.2 + noise)
                factor3 = ((nx_eased + (1 - ny_eased)) / 2 * 0.3 + noise)
                
                # Normalize factors
                total = factor1 + factor2 + factor3
                if total > 0:
                    factor1 /= total
                    factor2 /= total
                    factor3 /= total
                
                # Blend all three colors based on the complex factors
                color = tuple(
                    int(max(0, min(255, 
                        colors[0][i] * factor1 + 
                        colors[1][i] * factor2 + 
                        colors[2][i] * factor3
                    )))
                    for i in range(3)
                )
                
                draw.point((x, y), fill=color)

        # Apply additional blur for ultra-smooth gradients
        image = image.filter(ImageFilter.GaussianBlur(radius=4))
        
        return image

    def _image_to_jpeg_bytes(self, image: Image.Image, quality: int = 95) -> bytes:
        """Convert PIL Image to JPEG bytes.
        
        Args:
            image: PIL Image object
            quality: JPEG quality (1-100)
            
        Returns:
            JPEG image as bytes
        """
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=quality, optimize=True)
        jpeg_bytes = buffer.getvalue()
        
        # Check size (Spotify limit is 256KB)
        size_kb = len(jpeg_bytes) / 1024
        if size_kb > 256:
            logger.warning(f"Image size {size_kb:.1f}KB exceeds Spotify limit, reducing quality")
            # Reduce quality if needed
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG', quality=85, optimize=True)
            jpeg_bytes = buffer.getvalue()
        
        logger.info(f"Generated cover image: {len(jpeg_bytes)} bytes ({len(jpeg_bytes)/1024:.1f}KB)")
        return jpeg_bytes

