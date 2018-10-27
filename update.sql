-- --------------------------------------------------------
-- Host:                         awsdualsnakeapi.c4lsfupeyhhc.sa-east-1.rds.amazonaws.com
-- Server version:               5.6.37-log - MySQL Community Server (GPL)
-- Server OS:                    Linux
-- HeidiSQL Version:             9.4.0.5125
-- --------------------------------------------------------

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8 */;
/*!50503 SET NAMES utf8mb4 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;


-- Dumping database structure for pda
CREATE DATABASE IF NOT EXISTS `pda` /*!40100 DEFAULT CHARACTER SET latin1 */;
USE `pda`;

-- Dumping structure for table pda.badge
CREATE TABLE IF NOT EXISTS `badge` (
  `player_id` varchar(500) NOT NULL,
  `gym_id` int(11) NOT NULL,
  PRIMARY KEY (`player_id`,`gym_id`),
  CONSTRAINT `FK__player` FOREIGN KEY (`player_id`) REFERENCES `player` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- Data exporting was unselected.
-- Dumping structure for table pda.gym
CREATE TABLE IF NOT EXISTS `gym` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `server_id` varchar(500) DEFAULT '244845795336126465',
  `type_id` int(11) DEFAULT NULL,
  `holder_id` varchar(500) DEFAULT NULL,
  `pokemon_id` int(11) DEFAULT NULL,
  `date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `FK_gym_player` (`holder_id`),
  KEY `FK_gym_player_pokemon` (`pokemon_id`),
  KEY `FK_gym_type` (`type_id`),
  KEY `FK_gym_server` (`server_id`),
  CONSTRAINT `FK_gym_player` FOREIGN KEY (`holder_id`) REFERENCES `player` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `FK_gym_player_pokemon` FOREIGN KEY (`pokemon_id`) REFERENCES `player_pokemon` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `FK_gym_server` FOREIGN KEY (`server_id`) REFERENCES `server` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `FK_gym_type` FOREIGN KEY (`type_id`) REFERENCES `type` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=723 DEFAULT CHARSET=latin1;

-- Data exporting was unselected.
-- Dumping structure for table pda.item
CREATE TABLE IF NOT EXISTS `item` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `type` int(11) NOT NULL,
  `name` varchar(50) NOT NULL,
  `price` int(11) NOT NULL,
  `description` varchar(5000) NOT NULL,
  `value` int(11) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=latin1;

-- Data exporting was unselected.
-- Dumping structure for table pda.player
CREATE TABLE IF NOT EXISTS `player` (
  `id` varchar(500) CHARACTER SET latin1 NOT NULL,
  `name` varchar(10000) CHARACTER SET utf8 NOT NULL,
  `level` int(11) NOT NULL DEFAULT '1',
  `experience` bigint(20) NOT NULL DEFAULT '0',
  `money` int(11) NOT NULL DEFAULT '0',
  `pokemon_caught` int(11) NOT NULL DEFAULT '0',
  `exp_boost` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin;

-- Data exporting was unselected.
-- Dumping structure for table pda.player_item
CREATE TABLE IF NOT EXISTS `player_item` (
  `player_id` varchar(50) NOT NULL,
  `item_id` int(11) NOT NULL,
  `quantity` int(11) DEFAULT '0',
  PRIMARY KEY (`player_id`,`item_id`),
  KEY `FK_player_item_item` (`item_id`),
  CONSTRAINT `FK_player_item_item` FOREIGN KEY (`item_id`) REFERENCES `item` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `FK_player_item_player` FOREIGN KEY (`player_id`) REFERENCES `player` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- Data exporting was unselected.
-- Dumping structure for table pda.player_pokemon
CREATE TABLE IF NOT EXISTS `player_pokemon` (
  `id` int(11) NOT NULL,
  `player_id` varchar(500) NOT NULL DEFAULT '0',
  `pokemon_id` int(11) NOT NULL DEFAULT '0',
  `caught_with` int(11) DEFAULT '0',
  `selected` tinyint(4) NOT NULL DEFAULT '0',
  `in_gym` int(11) NOT NULL DEFAULT '0',
  `healing` timestamp NULL DEFAULT NULL,
  `level` int(11) NOT NULL DEFAULT '1',
  `experience` int(11) DEFAULT '0',
  `current_hp` int(11) DEFAULT '0',
  `iv_hp` int(11) DEFAULT '0',
  `iv_attack` int(11) DEFAULT '0',
  `iv_defense` int(11) DEFAULT '0',
  `iv_special_attack` int(11) DEFAULT '0',
  `iv_special_defense` int(11) DEFAULT '0',
  `iv_speed` int(11) DEFAULT '0',
  PRIMARY KEY (`id`,`player_id`),
  KEY `FK__pokemon` (`pokemon_id`),
  KEY `FK_player_pokemon_player` (`player_id`),
  CONSTRAINT `FK__pokemon` FOREIGN KEY (`pokemon_id`) REFERENCES `pokemon` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `FK_player_pokemon_player` FOREIGN KEY (`player_id`) REFERENCES `player` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- Data exporting was unselected.
-- Dumping structure for table pda.pokemon
CREATE TABLE IF NOT EXISTS `pokemon` (
  `id` int(11) NOT NULL,
  `identifier` varchar(255) DEFAULT NULL,
  `generation_id` int(11) NOT NULL,
  `evolves_from_species_id` int(11) DEFAULT '0',
  `evolved_at_level` int(11) DEFAULT '0',
  `evolution_chain_id` int(11) NOT NULL DEFAULT '0',
  `color_id` int(11) NOT NULL,
  `shape_id` int(11) NOT NULL,
  `habitat_id` int(11) NOT NULL,
  `gender_rate` int(11) NOT NULL,
  `capture_rate` int(11) NOT NULL,
  `base_happiness` int(11) NOT NULL,
  `is_baby` tinyint(4) NOT NULL DEFAULT '0',
  `hatch_counter` int(11) NOT NULL DEFAULT '0',
  `has_gender_differences` tinyint(4) NOT NULL DEFAULT '0',
  `growth_rate_id` int(11) NOT NULL,
  `forms_switchable` tinyint(4) NOT NULL,
  `order` int(11) NOT NULL,
  `conquest_order` int(11) NOT NULL,
  `enabled` tinyint(4) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- Data exporting was unselected.
-- Dumping structure for table pda.pokemon_stat
CREATE TABLE IF NOT EXISTS `pokemon_stat` (
  `pokemon_id` int(11) NOT NULL,
  `stat_id` int(11) NOT NULL,
  `base_stat` int(11) DEFAULT NULL,
  `effort` int(11) DEFAULT NULL,
  PRIMARY KEY (`pokemon_id`,`stat_id`),
  KEY `FK_pokemon_stats_stats` (`stat_id`),
  CONSTRAINT `FK_pokemon_stats_pokemons` FOREIGN KEY (`pokemon_id`) REFERENCES `pokemon` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `FK_pokemon_stats_stats` FOREIGN KEY (`stat_id`) REFERENCES `stat` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- Data exporting was unselected.
-- Dumping structure for table pda.pokemon_type
CREATE TABLE IF NOT EXISTS `pokemon_type` (
  `pokemon_id` int(11) NOT NULL DEFAULT '0',
  `type_id` int(11) NOT NULL DEFAULT '0',
  `slot` int(11) NOT NULL DEFAULT '0',
  PRIMARY KEY (`pokemon_id`,`slot`),
  KEY `FK_pokemon_type_type` (`type_id`),
  CONSTRAINT `FK_pokemon_type_pokemon` FOREIGN KEY (`pokemon_id`) REFERENCES `pokemon` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `FK_pokemon_type_type` FOREIGN KEY (`type_id`) REFERENCES `type` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- Data exporting was unselected.
-- Dumping structure for table pda.pokemon_yield_ev
CREATE TABLE IF NOT EXISTS `pokemon_yield_ev` (
  `pokemon_id` int(11) NOT NULL,
  `experience` int(11) NOT NULL,
  PRIMARY KEY (`pokemon_id`),
  CONSTRAINT `FK_pokemon_yield_ev_pokemon` FOREIGN KEY (`pokemon_id`) REFERENCES `pokemon` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- Data exporting was unselected.
-- Dumping structure for table pda.server
CREATE TABLE IF NOT EXISTS `server` (
  `id` varchar(500) NOT NULL,
  `prefix` varchar(10) NOT NULL DEFAULT 'p!',
  `spawn_channel` varchar(20) DEFAULT NULL,
  `afk_time` int(11) NOT NULL DEFAULT '75',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- Data exporting was unselected.
-- Dumping structure for table pda.stat
CREATE TABLE IF NOT EXISTS `stat` (
  `id` int(11) NOT NULL,
  `damage_class_id` int(11) NOT NULL,
  `identifier` varchar(255) NOT NULL,
  `is_battle_only` tinyint(4) NOT NULL,
  `game_index` int(11) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- Data exporting was unselected.
-- Dumping structure for table pda.type
CREATE TABLE IF NOT EXISTS `type` (
  `id` int(11) NOT NULL,
  `identifier` varchar(255) NOT NULL,
  `generation` int(11) NOT NULL,
  `damage_class_id` int(11) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- Data exporting was unselected.
-- Dumping structure for table pda.type_efficacy
CREATE TABLE IF NOT EXISTS `type_efficacy` (
  `damage_type_id` int(11) NOT NULL,
  `target_type_id` int(11) NOT NULL,
  `damage_factor` int(11) NOT NULL,
  PRIMARY KEY (`damage_type_id`,`target_type_id`),
  KEY `FK_type_efficacy_type_2` (`target_type_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- Data exporting was unselected.
/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IF(@OLD_FOREIGN_KEY_CHECKS IS NULL, 1, @OLD_FOREIGN_KEY_CHECKS) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
