import React from 'react';

const TeamCard = ({ team, onPlayerClick }) => {
  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h3 className="font-semibold text-lg mb-2">{team.name}</h3>
      <p className="text-sm text-gray-600 mb-2">Strategy: {team.strategy}</p>
      <div className="space-y-1">
        <h4 className="font-medium text-sm">Roster:</h4>
        {Object.entries(team.roster).map(([position, player]) =>
              <div key={position} className="text-xs text-gray-600">
              {position}: {player ? (
              <button
                onClick={() => onPlayerClick(player.id)}
                className="text-blue-600 hover:text-blue-800 transition-colors"
              >
                {player.name}
              </button>
            ) : (
              'Empty'
            )}
            </div>
            )}
      </div>
    </div>
  );
};

export default TeamCard;