const MONTHS = {
    1: "Styczeń",
    2: "Luty",
    3: "Marzec",
    4: "Kwiecień",
    5: "Maj",
    6: "Czerwiec",
    7: "Lipiec",
    8: "Sierpień",
    9: "Wrzesień",
    10: "Październik",
    11: "Listopad",
    12: "Grudzień"
};

const COLORS = {
    capex: '#8884d8',
    opex: '#82ca9d',
    consultation: '#ffc658'
};

class DashboardCharts extends React.Component {
    render() {
        const { data } = this.props;
        
        // Przekształcenie danych dla wykresu słupkowego
        const barChartData = Object.entries(data.monthly_data).map(([month, values]) => ({
            name: MONTHS[parseInt(month)],
            CAPEX: values.capex,
            OPEX: values.opex,
            Konsultacje: values.consultation
        }));

        // Przekształcenie danych dla wykresu kołowego
        const pieChartData = Object.entries(data.yearly_summary).map(([key, value]) => ({
            name: key === 'capex' ? 'CAPEX' : key === 'opex' ? 'OPEX' : 'Konsultacje',
            value: value
        }));

        // Przekształcenie danych nadgodzin
        const overtimePieData = Object.entries(data.overtime_data).map(([key, value]) => ({
            name: key.toUpperCase(),
            value: value
        }));

        return React.createElement('div', { className: 'space-y-8' },
            // Wykres słupkowy - godziny miesięczne
            React.createElement('div', { className: 'bg-white p-4 rounded-lg shadow' },
                React.createElement('h3', { className: 'text-lg font-bold mb-4' }, 'Godziny w miesiącach'),
                React.createElement('div', { className: 'h-64' },
                    React.createElement(Recharts.ResponsiveContainer, { width: '100%', height: '100%' },
                        React.createElement(Recharts.BarChart, { data: barChartData },
                            React.createElement(Recharts.CartesianGrid, { strokeDasharray: '3 3' }),
                            React.createElement(Recharts.XAxis, { dataKey: 'name' }),
                            React.createElement(Recharts.YAxis),
                            React.createElement(Recharts.Tooltip),
                            React.createElement(Recharts.Legend),
                            React.createElement(Recharts.Bar, { dataKey: 'CAPEX', fill: COLORS.capex }),
                            React.createElement(Recharts.Bar, { dataKey: 'OPEX', fill: COLORS.opex }),
                            React.createElement(Recharts.Bar, { dataKey: 'Konsultacje', fill: COLORS.consultation })
                        )
                    )
                )
            ),

            // Grid dla wykresów kołowych
            React.createElement('div', { className: 'grid grid-cols-1 md:grid-cols-2 gap-4' },
                // Wykres kołowy - podsumowanie roczne
                React.createElement('div', { className: 'bg-white p-4 rounded-lg shadow' },
                    React.createElement('h3', { className: 'text-lg font-bold mb-4' }, 'Podsumowanie roczne'),
                    React.createElement('div', { className: 'h-64' },
                        React.createElement(Recharts.ResponsiveContainer, { width: '100%', height: '100%' },
                            React.createElement(Recharts.PieChart,
                                null,
                                React.createElement(Recharts.Pie, {
                                    data: pieChartData,
                                    cx: '50%',
                                    cy: '50%',
                                    labelLine: false,
                                    label: ({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`,
                                    outerRadius: 80,
                                    fill: '#8884d8',
                                    dataKey: 'value'
                                }, 
                                    pieChartData.map((entry, index) =>
                                        React.createElement(Recharts.Cell, {
                                            key: `cell-${index}`,
                                            fill: Object.values(COLORS)[index]
                                        })
                                    )
                                ),
                                React.createElement(Recharts.Tooltip)
                            )
                        )
                    )
                ),

                // Wykres kołowy - nadgodziny
                React.createElement('div', { className: 'bg-white p-4 rounded-lg shadow' },
                    React.createElement('h3', { className: 'text-lg font-bold mb-4' }, 'Nadgodziny'),
                    React.createElement('div', { className: 'h-64' },
                        React.createElement(Recharts.ResponsiveContainer, { width: '100%', height: '100%' },
                            React.createElement(Recharts.PieChart,
                                null,
                                React.createElement(Recharts.Pie, {
                                    data: overtimePieData,
                                    cx: '50%',
                                    cy: '50%',
                                    labelLine: false,
                                    label: ({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`,
                                    outerRadius: 80,
                                    fill: '#8884d8',
                                    dataKey: 'value'
                                },
                                    React.createElement(Recharts.Cell, { fill: COLORS.capex }),
                                    React.createElement(Recharts.Cell, { fill: COLORS.opex })
                                ),
                                React.createElement(Recharts.Tooltip)
                            )
                        )
                    )
                )
            )
        );
    }
}

// Dodaj komponent do globalnego obiektu window
window.DashboardCharts = DashboardCharts;