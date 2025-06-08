import React from 'react'
import AccountSummary from '../components/AccountSummary'
import SignalTable from '../components/SignalTable'

function Home() {
    return (
        <div>
            <AccountSummary />
            <SignalTable />
        </div>
    )
}

export default Home