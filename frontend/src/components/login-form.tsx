'use client'

import { createClient } from '@/utils/supabase/client'
import { Button } from '@/components/ui/button'
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card"
import { useState } from 'react'
import { Loader2 } from 'lucide-react'

export default function LoginForm() {
    const [isLoading, setIsLoading] = useState(false)

    const handleLogin = async () => {
        setIsLoading(true)
        const supabase = createClient()
        await supabase.auth.signInWithOAuth({
            provider: 'google',
            options: {
                redirectTo: `${location.origin}/auth/callback`,
            },
        })
    }

    return (
        <Card className="w-full max-w-sm border-0 shadow-none sm:border sm:shadow-sm bg-background/60 backdrop-blur-sm">
            <CardHeader className="text-center space-y-2">
                <CardTitle className="text-2xl font-bold tracking-tight">Welcome back</CardTitle>
                <CardDescription className="text-muted-foreground/80">
                    Sign in to your account to continue managing your finances
                </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4">
                <Button
                    onClick={handleLogin}
                    disabled={isLoading}
                    className="w-full h-11 relative overflow-hidden group transition-all duration-300 hover:shadow-lg hover:shadow-primary/20"
                >
                    {isLoading ? (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-1000" />
                    )}
                    {!isLoading && (
                        <svg className="mr-2 h-4 w-4" aria-hidden="true" focusable="false" data-prefix="fab" data-icon="google" role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 488 512">
                            <path fill="currentColor" d="M488 261.8C488 403.3 391.1 504 248 504 110.8 504 0 393.2 0 256S110.8 8 248 8c66.8 0 123 24.5 166.3 64.9l-67.5 64.9C258.5 52.6 94.3 116.6 94.3 256c0 86.5 69.1 156.6 153.7 156.6 98.2 0 135-70.4 140.8-106.9H248v-85.3h236.1c2.3 12.7 3.9 24.9 3.9 41.4z"></path>
                        </svg>
                    )}
                    Sign in with Google
                </Button>
            </CardContent>
        </Card>
    )
}
