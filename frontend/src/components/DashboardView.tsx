import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Dashboard } from './Dashboard';
import { TransactionList } from './TransactionList';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { DollarSign, CreditCard, Activity, Wallet } from 'lucide-react';

interface DashboardStats {
    total_spent: number;
    budget: number;
    remaining: number;
    active_debts: number;
}

export function DashboardView({ refreshTrigger }: { refreshTrigger: number }) {
    const [stats, setStats] = useState<DashboardStats>({
        total_spent: 0,
        budget: 0,
        remaining: 0,
        active_debts: 0
    });

    useEffect(() => {
        const fetchStats = async () => {
            try {
                const res = await axios.get('http://localhost:8000/stats');
                setStats(res.data);
            } catch (error) {
                console.error("Error fetching stats:", error);
            }
        };
        fetchStats();
    }, [refreshTrigger]);

    const formatCurrency = (amount: number) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
        }).format(amount);
    };

    return (
        <div className="flex-1 space-y-4 p-4 pt-6">
            <div className="flex items-center justify-between space-y-2">
                <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
                <div className="flex items-center space-x-2">
                    {/* Date Range Picker could go here */}
                </div>
            </div>
            <Tabs defaultValue="overview" className="space-y-4">
                <TabsList>
                    <TabsTrigger value="overview">Overview</TabsTrigger>
                    <TabsTrigger value="analytics">Analytics</TabsTrigger>
                    <TabsTrigger value="reports" disabled>Reports</TabsTrigger>
                </TabsList>
                <TabsContent value="overview" className="space-y-4">
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                        <Card>
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium">Total Spent</CardTitle>
                                <DollarSign className="h-4 w-4 text-muted-foreground" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">{formatCurrency(stats.total_spent)}</div>
                                <p className="text-xs text-muted-foreground">Total expenses</p>
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium">Budget</CardTitle>
                                <Wallet className="h-4 w-4 text-muted-foreground" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">{formatCurrency(stats.budget)}</div>
                                <p className="text-xs text-muted-foreground">Total budget</p>
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium">Remaining</CardTitle>
                                <Activity className="h-4 w-4 text-muted-foreground" />
                            </CardHeader>
                            <CardContent>
                                <div className={`text-2xl font-bold ${stats.remaining < 0 ? 'text-red-500' : ''}`}>
                                    {formatCurrency(stats.remaining)}
                                </div>
                                <p className="text-xs text-muted-foreground">
                                    {stats.budget > 0 ? `${((stats.remaining / stats.budget) * 100).toFixed(1)}% of budget left` : 'No budget set'}
                                </p>
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium">Active Debts</CardTitle>
                                <CreditCard className="h-4 w-4 text-muted-foreground" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">{formatCurrency(stats.active_debts)}</div>
                                <p className="text-xs text-muted-foreground">To be collected</p>
                            </CardContent>
                        </Card>
                    </div>
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
                        <div className="col-span-4">
                            <Dashboard refreshTrigger={refreshTrigger} />
                        </div>
                        <div className="col-span-3">
                            <TransactionList refreshTrigger={refreshTrigger} />
                        </div>
                    </div>
                </TabsContent>
                <TabsContent value="analytics" className="space-y-4">
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
                        <div className="col-span-7">
                            <Card className="h-[400px] flex items-center justify-center text-muted-foreground">
                                Analytics View Placeholder
                            </Card>
                        </div>
                    </div>
                </TabsContent>
            </Tabs>
        </div>
    );
}
