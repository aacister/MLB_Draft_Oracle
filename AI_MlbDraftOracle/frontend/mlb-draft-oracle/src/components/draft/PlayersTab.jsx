import React, { useState, useMemo, useEffect, useRef } from 'react';
import { Search, Filter, ChevronUp, ChevronDown } from 'lucide-react';
import EmptyState from '../common/EmptyState';
//import { useDraft } from '../../hooks/useDraft.jsx';

const PlayersTab = ({ players, onSelectPlayer, highlightedPlayerId, setHighlightedPlayerId, draftHistory = [] }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [positionFilter, setPositionFilter] = useState('ALL');
  const [sortBy, setSortBy] = useState('name');
  const [sortDirection, setSortDirection] = useState('asc');
  const highlightedRowRef = useRef(null);

 // const { draftData, currentlyDrafting, draftPlayer, currentPick } = useDraft();

  useEffect(() => {
    // Clear highlight after 3 seconds
    if (highlightedPlayerId) {
      const timer = setTimeout(() => {
        setHighlightedPlayerId(null);
      }, 10000);
      return () => clearTimeout(timer);
    }
  }, [highlightedPlayerId, setHighlightedPlayerId]);

  useEffect(() => {
    // Scroll to and focus highlighted row
    if (highlightedPlayerId && highlightedRowRef.current) {
      highlightedRowRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      });
      highlightedRowRef.current.focus();

      // Set a timeout to clear the highlight after 20 seconds
      const timer = setTimeout(() => {
        setHighlightedPlayerId(null); // Clear the highlighted player ID
      }, 20000); // 20 seconds in milliseconds

      // Cleanup the timeout if the component unmounts or highlightedPlayerId changes
      return () => clearTimeout(timer);
    }
  }, [highlightedPlayerId, setHighlightedPlayerId]);

  const draftedPlayersMap = useMemo(() => {
    const map = new Map();
    if (draftHistory && Array.isArray(draftHistory)) {
      draftHistory.forEach(pick => {
        if (pick.selection) {
          map.set(pick.selection, pick.team);
        }
      });
    }
    return map;
  }, [draftHistory]);

  if (!players || !players.length) {
    return <EmptyState title="No draft board data available" />;
  }

  const allPlayers = players || [];

  // Get unique positions for filter dropdown
  const positions = useMemo(() => {
    const uniquePositions = [...new Set(allPlayers.map(p => p.position))];
    return uniquePositions.sort();
  }, [allPlayers]);

  // Define specific stat columns to display
  const statColumns = ['obp', 'r', 'rbi', 's', 'sb', 'slg', 'w', 'whip'];

  // Filter and sort players
  const filteredAndSortedPlayers = useMemo(() => {
    let filtered = allPlayers;

    // Apply search filter
    if (searchTerm) {
      filtered = filtered.filter(player =>
        player.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        player.team.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Apply position filter
    if (positionFilter !== 'ALL') {
      filtered = filtered.filter(player => player.position === positionFilter);
    }

    // Apply sorting
    filtered.sort((a, b) => {
      let aValue, bValue;

      if (sortBy === 'name') {
        aValue = a.name || '';
        bValue = b.name || '';
        return sortDirection === 'asc' 
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }

      if (sortBy === 'team') {
        aValue = a.team || '';
        bValue = b.team || '';
        return sortDirection === 'asc'
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }

      if (sortBy === 'position') {
        aValue = a.position || '';
        bValue = b.position || '';
        return sortDirection === 'asc'
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }

      if (sortBy === 'drafted') {
        aValue = a.is_drafted ? (draftedPlayersMap.get(a.name) || 'Yes') : '';
        bValue = b.is_drafted ? (draftedPlayersMap.get(b.name) || 'Yes') : '';
        return sortDirection === 'asc'
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }

      // Handle stat sorting
      if (statColumns.includes(sortBy)) {
        aValue = parseFloat(a.stats?.[sortBy]) || 0;
        bValue = parseFloat(b.stats?.[sortBy]) || 0;
        return sortDirection === 'asc' ? aValue - bValue : bValue - aValue;
      }

      return 0;
    });

    return filtered;
  }, [allPlayers, searchTerm, positionFilter, sortBy, sortDirection,  draftedPlayersMap]);

  const handleSort = (column) => {
    if (sortBy === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortDirection('asc');
    }
  };

  const formatStatValue = (value) => {
    if (value == null) return '-';
    if (typeof value === 'number') {
      return value % 1 === 0 ? value.toString() : value.toFixed(3);
    }
    return value.toString();
  };

  const getPositionColor = (position) => {
    const colors = {
      '1B': 'text-red-600 bg-red-50',
      SS: 'text-green-600 bg-green-50',
      OF: 'text-blue-600 bg-blue-50',
      C: 'text-yellow-600 bg-yellow-50',
      P: 'text-purple-600 bg-purple-50'
    };
    return colors[position] || 'text-gray-600 bg-gray-50';
  };

  const getDraftedTeam = (player) => {
    if (!player.is_drafted) return '';
    return draftedPlayersMap.get(player.name) || '';
  };

  const SortButton = ({ column, children }) => (
    <button
      onClick={() => handleSort(column)}
      className="flex items-center gap-1 text-left font-medium text-gray-900 hover:text-blue-600 transition-colors"
    >
      {children}
      {sortBy === column && (
        sortDirection === 'asc' ? 
          <ChevronUp className="h-4 w-4" /> : 
          <ChevronDown className="h-4 w-4" />
      )}
    </button>
  );

  const formatStatLabel = (stat) => {
    const labels = {
      'obp': 'OBP',
      'r': 'R',
      'rbi': 'RBI',
      's': 'S',
      'sb': 'SB',
      'slg': 'SLG',
      'w': 'W',
      'whip': 'WHIP'
    };
    return labels[stat] || stat.toUpperCase();
  };

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-6">
        <h2 className="text-xl font-bold text-red-800 mb-4 sm:mb-0">
          Players ({filteredAndSortedPlayers.length})
        </h2>
        
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
            <input
              type="text"
              placeholder="Search players..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm w-64"
            />
          </div>

          <div className="relative">
            <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
            <select
              value={positionFilter}
              onChange={(e) => setPositionFilter(e.target.value)}
              className="pl-10 pr-8 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 text-sm appearance-none bg-white"
            >
              <option value="ALL">All Positions</option>
              {positions.map(pos => (
                <option key={pos} value={pos}>{pos}</option>
              ))}
            </select>
          </div>
        </div>
      </div>
{/*}
      {currentPick && !draftData?.is_complete && (
        <div className="mb-4 bg-blue-50 border border-blue-200 rounded-lg p-3">
          <p className="text-sm text-blue-800">
            <strong>Current Pick:</strong> Round {currentPick.round}, Pick {currentPick.pick} - {currentPick.team}
          </p>
        </div>
      )}
*/}
      {filteredAndSortedPlayers.length === 0 ? (
        <EmptyState 
          title="No players found"
          description="Try adjusting your search or filter criteria"
        />
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    <SortButton column="name">Name</SortButton>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    <SortButton column="team">Team</SortButton>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    <SortButton column="position">Position</SortButton>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    <SortButton column="drafted">Drafted?</SortButton>
                  </th>
                  {statColumns.map(statKey => (
                    <th key={statKey} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      <SortButton column={statKey}>
                        {formatStatLabel(statKey)}
                      </SortButton>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredAndSortedPlayers.map((player, index) => (
                  <tr key={player.id} 
                      ref={player.id === highlightedPlayerId ? highlightedRowRef : null}
                      tabIndex={player.id === highlightedPlayerId ? 0 : -1}
                      className={`
                        ${index % 2 === 0 ? 'bg-white' : 'bg-gray-50'} 
                        hover:bg-blue-50 transition-colors
                        ${player.id === highlightedPlayerId ? 'bg-yellow-100 outline-none ring-2 ring-yellow-400' : ''}
                      `}
                      >
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">{player.name}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">{player.team}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getPositionColor(player.position)}`}>
                        {player.position}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">
                        {getDraftedTeam(player) && (
                          <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full text-red-900  ">
                            {getDraftedTeam(player)}
                          </span>
                        )}
                      </div>
                    </td>
                    {statColumns.map(statKey => (
                      <td key={statKey} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatStatValue(player.stats?.[statKey])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default PlayersTab;

