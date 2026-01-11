'use client'

import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { DollarSign, Euro, PoundSterling, Wallet, TrendingUp, CreditCard } from 'lucide-react'

// Randomize positions and delays for a natural floating effect
const randomPosition = () => Math.floor(Math.random() * 80) + 10 // 10% to 90%
const randomDelay = () => Math.random() * 5
const randomDuration = () => Math.floor(Math.random() * 10) + 10 // 10s to 20s

interface FloatingIconProps {
    Icon: React.ElementType
    delay: number
    duration: number
    top: number
    left: number
    size: number
}

const FloatingIcon = ({ Icon, delay, duration, top, left, size }: FloatingIconProps) => {
    return (
        <motion.div
            className="absolute text-[#69f0ae]/20"
            initial={{ top: `${top}%`, left: `${left}%`, opacity: 0, scale: 0.5, y: 0 }}
            animate={{
                opacity: [0, 0.4, 0],
                scale: [0.5, 1, 0.5],
                y: [-20, -100, -20]
            }}
            transition={{
                duration: duration,
                repeat: Infinity,
                delay: delay,
                ease: "easeInOut"
            }}
            style={{
                width: size,
                height: size,
            }}
        >
            <Icon size={size} />
        </motion.div>
    )
}

export const MoneyAnimation = () => {
    const [mounted, setMounted] = useState(false)

    // Icons pool
    const icons = [DollarSign, Euro, PoundSterling, Wallet, TrendingUp, CreditCard]

    useEffect(() => {
        setMounted(true)
    }, [])

    if (!mounted) return null

    return (
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
            {/* Generate multiple floating icons */}
            {Array.from({ length: 15 }).map((_, i) => {
                const Icon = icons[i % icons.length]
                return (
                    <FloatingIcon
                        key={i}
                        Icon={Icon}
                        delay={randomDelay()}
                        duration={randomDuration()}
                        top={randomPosition()}
                        left={randomPosition()}
                        size={Math.floor(Math.random() * 40) + 20} // 20px to 60px
                    />
                )
            })}
        </div>
    )
}
