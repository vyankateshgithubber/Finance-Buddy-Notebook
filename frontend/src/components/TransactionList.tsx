import React, { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { Clock, DollarSign, Tag } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"

interface Transaction {
    id: number;
    timestamp: string;
    description: string;
    amount: number;
    category: string;
    split_details?: string;
}

export function TransactionList({ refreshTrigger }: { refreshTrigger: number }) {
    const [transactions, setTransactions] = useState<Transaction[]>([]);
    const [filteredTransactions, setFilteredTransactions] = useState<Transaction[]>([]);
    const [searchQuery, setSearchQuery] = useState("");
    const [categoryFilter, setCategoryFilter] = useState("all");
    const [categories, setCategories] = useState<string[]>([]);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const res = await api.get('/transactions');
                setTransactions(res.data);
            } catch (error) {
                console.error("Error fetching transactions:", error);
            }
        };
        fetchData();
    }, [refreshTrigger]);

    useEffect(() => {
        let result = transactions;

        if (searchQuery) {
            const query = searchQuery.toLowerCase();
            result = result.filter(t =>
                t.description.toLowerCase().includes(query) ||
                t.category.toLowerCase().includes(query)
            );
        }

        if (categoryFilter && categoryFilter !== "all") {
            result = result.filter(t => t.category === categoryFilter);
        }

        setFilteredTransactions(result);
    }, [searchQuery, categoryFilter, transactions]);

    const getInitials = (name: string) => {
        return name.substring(0, 2).toUpperCase();
    }

    return (
        <Card className="col-span-3 h-full flex flex-col">
            <CardHeader>
                <CardTitle>Recent Transactions</CardTitle>
                <CardDescription>
                    You made {filteredTransactions.length} transactions this month.
                </CardDescription>
                <div className="flex gap-2 mt-2">
                    <div className="relative flex-1">
                        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                        <Input
                            placeholder="Search..."
                            className="pl-9 h-9 bg-muted/50"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                    </div>
                    <Select value={categoryFilter} onValueChange={setCategoryFilter}>
                        <SelectTrigger className="w-[130px] h-9 bg-muted/50">
                            <div className="flex items-center gap-2">
                                <Filter className="h-3.5 w-3.5 text-muted-foreground" />
                                <SelectValue placeholder="Category" />
                            </div>
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="all">All</SelectItem>
                            {categories.map(cat => (
                                <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
            </CardHeader>
            <CardContent className="flex-1 overflow-hidden p-0">
                <ScrollArea className="h-[400px] px-6">
                    <div className="space-y-8 pb-6">
                        {filteredTransactions.length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-8 text-muted-foreground space-y-2">
                                <Search className="h-8 w-8 opacity-20" />
                                <p>No transactions found.</p>
                            </div>
                        ) : (
                            filteredTransactions.map((t) => (
                                <div key={t.id} className="flex items-center">
                                    <Avatar className="h-9 w-9">
                                        <AvatarFallback className="bg-primary/10 text-primary font-medium text-xs">
                                            {getInitials(t.category)}
                                        </AvatarFallback>
                                    </Avatar>
                                    <div className="ml-4 space-y-1">
                                        <p className="text-sm font-medium leading-none">{t.description}</p>
                                        <p className="text-xs text-muted-foreground">
                                            {t.category} • {t.timestamp}
                                        </p>
                                    </div>
                                    <div className="ml-auto font-medium">
                                        -${t.amount.toFixed(2)}
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </ScrollArea>
            </CardContent>
        </Card>
    );
}
