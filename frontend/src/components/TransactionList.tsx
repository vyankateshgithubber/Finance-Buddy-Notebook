import React, { useEffect, useState } from 'react';
import axios from 'axios';
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

    useEffect(() => {
        const fetchData = async () => {
            try {
                const res = await axios.get('http://localhost:8000/transactions');
                setTransactions(res.data);
            } catch (error) {
                console.error("Error fetching transactions:", error);
            }
        };
        fetchData();
    }, [refreshTrigger]);

    return (
        <Card className="h-full flex flex-col shadow-md border-0 overflow-hidden">
            <CardHeader className="pb-2 bg-muted/30">
                <CardTitle className="text-lg font-semibold">Recent Transactions</CardTitle>
            </CardHeader>
            <CardContent className="flex-1 p-0 overflow-hidden">
                <ScrollArea className="h-full p-4">
                    <div className="space-y-3">
                        {transactions.length === 0 ? (
                            <p className="text-center text-muted-foreground py-8">No transactions yet.</p>
                        ) : (
                            transactions.map((t) => (
                                <div key={t.id} className="flex items-center justify-between p-3 hover:bg-muted/50 rounded-lg border transition-colors group">
                                    <div className="flex flex-col gap-1">
                                        <span className="font-medium text-foreground">{t.description}</span>
                                        <div className="flex items-center gap-3 text-xs text-muted-foreground">
                                            <span className="flex items-center gap-1">
                                                <Clock size={12} /> {t.timestamp}
                                            </span>
                                            <span className="flex items-center gap-1 px-2 py-0.5 bg-blue-50 text-blue-600 rounded-full border border-blue-100">
                                                <Tag size={12} /> {t.category}
                                            </span>
                                        </div>
                                    </div>
                                    <div className="font-bold text-foreground flex items-center">
                                        <DollarSign size={14} className="text-muted-foreground" />
                                        {t.amount.toFixed(2)}
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
