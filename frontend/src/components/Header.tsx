import React from 'react';
import { Search, Bell } from 'lucide-react';
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ModeToggle } from "@/components/mode-toggle"
import { UserProfile } from "@/components/user-profile"

export function Header() {
    return (
        <header className="flex items-center justify-between border-b px-6 py-3 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
            <div className="flex items-center gap-4">
                <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
                    FrugalAgent
                </h1>
                <nav className="hidden md:flex items-center gap-4 text-sm font-medium text-muted-foreground">
                    <a href="#" className="text-foreground transition-colors hover:text-foreground">Overview</a>
                    <a href="#" className="transition-colors hover:text-foreground">Transactions</a>
                    <a href="#" className="transition-colors hover:text-foreground">Settings</a>
                </nav>
            </div>

            <div className="flex items-center gap-4">
                <div className="relative hidden sm:block w-64">
                    <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                        type="search"
                        placeholder="Search..."
                        className="pl-9 h-9 bg-muted/50 border-none focus-visible:bg-background transition-all duration-200"
                    />
                </div>

                <Button variant="ghost" size="icon" className="h-9 w-9 text-muted-foreground hover:text-foreground">
                    <Bell className="h-4 w-4" />
                </Button>

                <ModeToggle />

                <UserProfile />
            </div>
        </header>
    );
}
