'use client'

import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'

export const WormholeAnimation = () => {
    const [mounted, setMounted] = useState(false)

    useEffect(() => {
        setMounted(true)
    }, [])

    if (!mounted) {
        return <div className="absolute inset-0 z-50 bg-black" />
    }

    // Generate fewer stars for a cleaner look
    const stars = Array.from({ length: 150 }).map((_, i) => {
        const angle = Math.random() * 360
        const velocity = Math.random() * 0.3 + 0.2 // Slower velocity range
        return {
            id: i,
            angle,
            initialR: Math.random() * 50,
            velocity,
            size: Math.random() * 1.5 + 0.5, // Slightly smaller
            color: i % 10 === 0 ? '#b3e5fc' : '#ffffff',
        }
    })

    return (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-black overflow-hidden perspective-[1000px]">
            {/* Removed Central Singularity Flash for subtlety */}

            <div className="relative w-full h-full flex items-center justify-center">
                {stars.map((star) => (
                    <motion.div
                        key={star.id}
                        initial={{
                            x: 0,
                            y: 0,
                            opacity: 0,
                            scale: 0.1
                        }}
                        animate={{
                            x: Math.cos(star.angle * (Math.PI / 180)) * 1200,
                            y: Math.sin(star.angle * (Math.PI / 180)) * 1200,
                            opacity: [0, 0.7, 0], // Reduced max opacity
                            scale: [0.1, 4] // Reduced scaling effect
                        }}
                        transition={{
                            duration: 2 / star.velocity, // Slower duration
                            repeat: Infinity,
                            ease: "easeInOut", // Smoother easing
                            delay: Math.random() * 2,
                        }}
                        style={{
                            position: 'absolute',
                            width: `${star.size}px`,
                            height: `${star.size * 15}px`, // Shorter trails
                            backgroundColor: star.color,
                            borderRadius: '50%',
                            rotate: `${star.angle + 90}deg`,
                        }}
                    />
                ))}
            </div>
        </div>
    )
}
