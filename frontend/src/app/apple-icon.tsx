import { ImageResponse } from 'next/og';

// Image metadata - Apple recommends 180x180 for apple-touch-icon
export const size = {
    width: 180,
    height: 180,
};

export const contentType = 'image/png';

// Apple icon generation
export default function AppleIcon() {
    return new ImageResponse(
        (
            <div
                style={{
                    width: '100%',
                    height: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: 'linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 50%, #000000 100%)',
                    borderRadius: '40px',
                    position: 'relative',
                }}
            >
                {/* Overlay gradient */}
                <div
                    style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        background: 'linear-gradient(to top right, rgba(255,255,255,0) 0%, rgba(255,255,255,0.08) 100%)',
                        borderRadius: '40px',
                    }}
                />
                {/* AudioLines Icon - scaled up */}
                <svg
                    width="100"
                    height="100"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="white"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    style={{ position: 'relative', zIndex: 10 }}
                >
                    <path d="M2 10v3" />
                    <path d="M6 6v11" />
                    <path d="M10 3v18" />
                    <path d="M14 8v7" />
                    <path d="M18 5v13" />
                    <path d="M22 10v3" />
                </svg>
            </div>
        ),
        {
            ...size,
        }
    );
}
