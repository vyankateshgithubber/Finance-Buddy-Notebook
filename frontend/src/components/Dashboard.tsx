import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface CategoryTotal {
    category: string;
    total: number;
    [key: string]: string | number;
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d', '#ffc658'];

export function Dashboard({ refreshTrigger }: { refreshTrigger: number }) {
    const [data, setData] = useState<CategoryTotal[]>([]);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const res = await axios.get('http://localhost:8000/insights');
                setData(res.data);
            } catch (error) {
                console.error("Error fetching insights:", error);
            }
        };
        fetchData();
    }, [refreshTrigger]);

    return (
        <Card className="h-full shadow-md border-0">
            <CardHeader className="pb-2">
                <CardTitle className="text-lg font-semibold">Spending by Category</CardTitle>
            </CardHeader>
            <CardContent className="h-[calc(100%-4rem)]">
                {data.length === 0 ? (
                    <div className="h-full flex items-center justify-center text-muted-foreground">
                        No data available
                    </div>
                ) : (
                    <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                            <Pie
                                data={data}
                                cx="50%"
                                cy="50%"
                                innerRadius={60}
                                outerRadius={80}
                                paddingAngle={5}
                                dataKey="total"
                            >
                                {data.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                ))}
                            </Pie>
                            <Tooltip
                                formatter={(value: number) => `$${value.toFixed(2)}`}
                                contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                            />
                            <Legend verticalAlign="bottom" height={36} />
                        </PieChart>
                    </ResponsiveContainer>
                )}
            </CardContent>
        </Card>
    );
}
