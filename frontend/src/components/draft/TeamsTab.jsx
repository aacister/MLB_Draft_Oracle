import React from 'react';
import TeamCard from './TeamCard';
import EmptyState from '../common/EmptyState';

const TeamsTab = ({ teams, setHighlightedPlayerId, setActiveTab }) => {
  const handlePlayerClick = (playerId) => {
    setHighlightedPlayerId(playerId);
    setActiveTab('draft');
  };


  if (!teams || !teams.length) {
    return <EmptyState title="No teams data available" />;
  }


  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {teams.map((team) => (
        <TeamCard key={team.name}
         team={team}
         onPlayerClick={handlePlayerClick}
          />
      ))}
    </div>
  );
};

export default TeamsTab;

