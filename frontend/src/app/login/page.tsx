import LoginForm from '@/components/login-form'
import { Command } from "lucide-react"
import { MoneyAnimation } from '@/components/money-animation'
import Image from 'next/image'

export default function LoginPage() {
    return (
        <div className="container relative h-screen flex-col items-center justify-center grid lg:max-w-none lg:grid-cols-2 lg:px-0">

            {/* Left Side: Branding (Visible on Desktop) */}
            <div className="relative hidden h-full flex-col bg-zinc-900 p-10 text-white lg:flex dark:border-r overflow-hidden">
                {/* Background Gradient */}
                <div className="absolute inset-0 bg-gradient-to-br from-[#0f2e1f] via-[#154a33] to-[#0b2419] z-0" />

                {/* Rupee Note Texture Overlay */}
                <div className="absolute inset-0 z-0 opacity-20 mix-blend-overlay pointer-events-none">
                    <Image
                        src="/rupee-note.png"
                        alt="Rupee Note Texture"
                        fill
                        className="object-cover"
                        priority
                    />
                </div>

                {/* Subtle Radial Gradient Overlay for Depth */}
                <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-[#34d399]/20 via-transparent to-transparent opacity-60 z-0" />

                <div className="relative z-10 w-full h-full flex flex-col">
                    <MoneyAnimation />

                    {/* Logo Area */}
                    <div className="relative z-20 flex items-center space-x-2">
                        <div className="p-2 bg-white/10 rounded-lg backdrop-blur-sm border border-white/10 shadow-xl">
                            <Command className="h-6 w-6 text-[#69f0ae]" />
                        </div>
                        <span className="text-2xl font-bold tracking-tight text-[#e8f5e9]">FrugalAgent</span>
                    </div>

                    {/* Quote Area with Glassmorphism */}
                    <div className="relative z-20 mt-auto">
                        <div className="relative p-6 bg-[#0f2e1f]/40 backdrop-blur-md rounded-xl border border-[#34d399]/20 shadow-2xl">
                            <blockquote className="space-y-2">
                                <p className="text-lg font-light leading-relaxed text-[#e8f5e9]">
                                    &ldquo;This AI finance agent has completely transformed how I track my expenses. It feels like having a personal accountant in my pocket.&rdquo;
                                </p>
                                <footer className="text-sm font-medium text-[#69f0ae] flex items-center gap-2">
                                    <div className="h-px w-8 bg-[#69f0ae]/50" />
                                    Sofia Davis
                                </footer>
                            </blockquote>
                        </div>
                    </div>
                </div>
            </div>

            {/* Left Side: Login Form */}
            <div className="relative lg:p-8 flex items-center justify-center h-full bg-background">
                {/* Subtle Background Pattern */}
                <div className="absolute inset-0 h-full w-full bg-white dark:bg-black bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] z-0" />

                <div className="relative z-10 mx-auto flex w-full flex-col justify-center space-y-6 sm:w-[350px]">
                    <LoginForm />
                    <p className="px-8 text-center text-sm text-muted-foreground">
                        By clicking continue, you agree to our{" "}
                        <a href="/terms" className="underline underline-offset-4 hover:text-primary">
                            Terms of Service
                        </a>{" "}
                        and{" "}
                        <a href="/privacy" className="underline underline-offset-4 hover:text-primary">
                            Privacy Policy
                        </a>
                        .
                    </p>
                </div>
            </div>
        </div>
    )
}
